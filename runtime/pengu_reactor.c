/* pengu_reactor.c — explicit user-space reactor for std.reactor.
 *
 * The C half only moves readiness and work tokens; the scheduling policy
 * (tasks, timers, what to resume) lives in std/reactor.pengu.  Linux uses
 * epoll + eventfd; other POSIX systems use poll + a self-pipe.  Windows uses
 * WSAEventSelect + WSAWaitForMultipleEvents with a wake event and a Win32
 * thread pool; std.net itself is still POSIX-only.
 *
 * The pool is private to the reactor on purpose: pengu_runtime.c is compiled
 * twice (threads on/off), and reusing its pool symbols here would either
 * duplicate them or force a link-time choice.
 */
#include "pengu_runtime.h"

#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#if defined(_WIN32)

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

typedef struct PenguWinJob {
  void (*fn)(void *);
  void *ctx;
  int64_t task_id;
  int64_t token;
  struct PenguWinJob *next;
} PenguWinJob;

typedef struct PenguWinDone {
  int64_t task_id;
  int64_t token;
  struct PenguWinDone *next;
} PenguWinDone;

typedef struct PenguWinEntry {
  SOCKET fd;
  WSAEVENT event;
  int64_t token;
  int events;
} PenguWinEntry;

#define PENGU_WIN_MAX_EVENTS 63

struct PenguReactor {
  DWORD owner;
  WSAEVENT wake_event;
  int workers;
  int closing;

  CRITICAL_SECTION lock;
  CONDITION_VARIABLE work_cv;
  CONDITION_VARIABLE idle_cv;
  PenguWinJob *jobs_head;
  PenguWinJob *jobs_tail;
  int active_jobs;
  HANDLE *threads;

  CRITICAL_SECTION done_lock;
  PenguWinDone *done_head;
  PenguWinDone *done_tail;

  PenguWinEntry entries[PENGU_WIN_MAX_EVENTS];
  int entry_count;
};

static DWORD WINAPI pengu_win_worker(LPVOID arg)
{
  PenguReactor *r = (PenguReactor *)arg;
  for (;;)
  {
    PenguWinJob *job;
    EnterCriticalSection(&r->lock);
    while (!r->closing && r->jobs_head == NULL)
      SleepConditionVariableCS(&r->work_cv, &r->lock, INFINITE);
    if (r->closing && r->jobs_head == NULL)
    {
      LeaveCriticalSection(&r->lock);
      break;
    }
    job = r->jobs_head;
    r->jobs_head = job->next;
    if (r->jobs_head == NULL)
      r->jobs_tail = NULL;
    r->active_jobs++;
    LeaveCriticalSection(&r->lock);

    job->fn(job->ctx);

    EnterCriticalSection(&r->done_lock);
    PenguWinDone *done = (PenguWinDone *)calloc(1, sizeof(*done));
    if (done != NULL)
    {
      done->task_id = job->task_id;
      done->token = job->token;
      if (r->done_tail == NULL)
        r->done_head = done;
      else
        r->done_tail->next = done;
      r->done_tail = done;
    }
    LeaveCriticalSection(&r->done_lock);
    free(job);

    EnterCriticalSection(&r->lock);
    r->active_jobs--;
    WakeAllConditionVariable(&r->idle_cv);
    LeaveCriticalSection(&r->lock);
    WSASetEvent(r->wake_event);
  }
  return 0;
}

PenguReactor *pengu_c_reactor_new(int workers)
{
  WSADATA wsa;
  PenguReactor *r;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0)
    return NULL;
  r = (PenguReactor *)calloc(1, sizeof(*r));
  if (r == NULL)
  {
    WSACleanup();
    return NULL;
  }
  r->owner = GetCurrentThreadId();
  r->workers = workers > 0 ? workers : 2;
  r->wake_event = WSACreateEvent();
  if (r->wake_event == WSA_INVALID_EVENT)
  {
    free(r);
    WSACleanup();
    return NULL;
  }
  InitializeCriticalSection(&r->lock);
  InitializeConditionVariable(&r->work_cv);
  InitializeConditionVariable(&r->idle_cv);
  InitializeCriticalSection(&r->done_lock);
  r->threads = (HANDLE *)calloc((size_t)r->workers, sizeof(HANDLE));
  if (r->threads == NULL)
  {
    WSACloseEvent(r->wake_event);
    DeleteCriticalSection(&r->lock);
    DeleteCriticalSection(&r->done_lock);
    free(r);
    WSACleanup();
    return NULL;
  }
  for (int i = 0; i < r->workers; i++)
  {
    r->threads[i] = CreateThread(NULL, 0, pengu_win_worker, r, 0, NULL);
    if (r->threads[i] == NULL)
    {
      r->closing = 1;
      for (int j = 0; j < i; j++)
      {
        WaitForSingleObject(r->threads[j], INFINITE);
        CloseHandle(r->threads[j]);
      }
      free(r->threads);
      WSACloseEvent(r->wake_event);
      DeleteCriticalSection(&r->lock);
      DeleteCriticalSection(&r->done_lock);
      free(r);
      WSACleanup();
      return NULL;
    }
  }
  return r;
}

int pengu_c_reactor_is_owner(void *r)
{
    PenguReactor *rr = (PenguReactor *)r;
  return r != NULL && GetCurrentThreadId() == rr->owner;
}

void pengu_c_reactor_free(void *r)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL)
    return;
  EnterCriticalSection(&rr->lock);
  rr->closing = 1;
  WakeAllConditionVariable(&rr->work_cv);
  LeaveCriticalSection(&rr->lock);
  for (int i = 0; i < rr->workers; i++)
  {
    if (rr->threads[i] != NULL)
    {
      WaitForSingleObject(rr->threads[i], INFINITE);
      CloseHandle(rr->threads[i]);
    }
  }
  free(rr->threads);
  for (int i = 0; i < rr->entry_count; i++)
  {
    WSAEventSelect(rr->entries[i].fd, NULL, 0);
    WSACloseEvent(rr->entries[i].event);
  }
  PenguWinJob *job = rr->jobs_head;
  while (job != NULL)
  {
    PenguWinJob *next = job->next;
    free(job);
    job = next;
  }
  PenguWinDone *done = rr->done_head;
  while (done != NULL)
  {
    PenguWinDone *next = done->next;
    free(done);
    done = next;
  }
  WSACloseEvent(rr->wake_event);
  DeleteCriticalSection(&rr->lock);
  DeleteCriticalSection(&rr->done_lock);
  free(r);
  WSACleanup();
}

int pengu_c_reactor_add(void *r, int fd, int events, int64_t token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || fd < 0 || rr->entry_count >= PENGU_WIN_MAX_EVENTS)
    return -1;
  for (int i = 0; i < rr->entry_count; i++)
    if (rr->entries[i].fd == (SOCKET)fd)
      return -1;
  WSAEVENT ev = WSACreateEvent();
  if (ev == WSA_INVALID_EVENT)
    return -1;
  long mask = 0;
  if (events & 1)
    mask |= FD_READ | FD_ACCEPT | FD_CLOSE;
  if (events & 2)
    mask |= FD_WRITE | FD_CONNECT | FD_CLOSE;
  if (WSAEventSelect((SOCKET)fd, ev, mask) != 0)
  {
    WSACloseEvent(ev);
    return -1;
  }
  PenguWinEntry *e = &rr->entries[rr->entry_count++];
  e->fd = (SOCKET)fd;
  e->event = ev;
  e->token = token;
  e->events = events;
  return 0;
}

int pengu_c_reactor_del(void *r, int fd)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL)
    return -1;
  for (int i = 0; i < rr->entry_count; i++)
  {
    if (rr->entries[i].fd == (SOCKET)fd)
    {
      WSAEventSelect(rr->entries[i].fd, NULL, 0);
      WSACloseEvent(rr->entries[i].event);
      rr->entries[i] = rr->entries[--rr->entry_count];
      return 0;
    }
  }
  return -1;
}

int pengu_c_reactor_wait(void *r, int timeout_ms, int64_t *tokens, int cap)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || tokens == NULL || cap <= 0)
    return -1;
  WSAEVENT events[PENGU_WIN_MAX_EVENTS + 1];
  int map[PENGU_WIN_MAX_EVENTS + 1];
  int count = 1;
  events[0] = rr->wake_event;
  map[0] = -1;
  for (int i = 0; i < rr->entry_count && count <= PENGU_WIN_MAX_EVENTS; i++)
  {
    events[count] = rr->entries[i].event;
    map[count] = i;
    count++;
  }
  DWORD rc = WSAWaitForMultipleEvents((DWORD)count, events, FALSE,
                                     timeout_ms < 0 ? WSA_INFINITE : (DWORD)timeout_ms,
                                     FALSE);
  if (rc == WSA_WAIT_TIMEOUT)
    return 0;
  if (rc == WSA_WAIT_FAILED)
    return -1;
  DWORD first = rc - WSA_WAIT_EVENT_0;
  int out = 0;
  if (first == 0)
  {
    /* A completion woke us: let std.reactor drain the queue; socket readiness
       is picked up by the next wait. */
    WSAResetEvent(rr->wake_event);
    return 0;
  }
  int idx = map[first];
  if (idx >= 0)
  {
    WSANETWORKEVENTS ne;
    if (WSAEnumNetworkEvents(rr->entries[idx].fd, rr->entries[idx].event, &ne) == 0 &&
        ne.lNetworkEvents != 0 && out < cap)
    {
      tokens[out++] = rr->entries[idx].token;
    }
    WSAEventSelect(rr->entries[idx].fd, NULL, 0);
    WSACloseEvent(rr->entries[idx].event);
    rr->entries[idx] = rr->entries[--rr->entry_count];
  }
  return out;
}

int pengu_c_reactor_post(void *r, int64_t task_id, int64_t token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL)
    return -1;
  PenguWinDone *done = (PenguWinDone *)calloc(1, sizeof(*done));
  if (done == NULL)
    return -1;
  done->task_id = task_id;
  done->token = token;
  EnterCriticalSection(&rr->done_lock);
  if (rr->done_tail == NULL)
    rr->done_head = done;
  else
    rr->done_tail->next = done;
  rr->done_tail = done;
  LeaveCriticalSection(&rr->done_lock);
  WSASetEvent(rr->wake_event);
  return 0;
}

int pengu_c_reactor_take(void *r, int64_t *task_id, int64_t *token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || task_id == NULL || token == NULL)
    return 0;
  EnterCriticalSection(&rr->done_lock);
  PenguWinDone *done = rr->done_head;
  if (done == NULL)
  {
    LeaveCriticalSection(&rr->done_lock);
    return 0;
  }
  rr->done_head = done->next;
  if (rr->done_head == NULL)
    rr->done_tail = NULL;
  *task_id = done->task_id;
  *token = done->token;
  LeaveCriticalSection(&rr->done_lock);
  free(done);
  return 1;
}

int64_t pengu_c_reactor_now_ms(void)
{
  return (int64_t)GetTickCount64();
}

int pengu_c_reactor_offload(void *r, void (*fn)(void *), void *ctx,
                            int64_t task_id, int64_t token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || fn == NULL)
    return -1;
  PenguWinJob *job = (PenguWinJob *)calloc(1, sizeof(*job));
  if (job == NULL)
    return -1;
  job->fn = fn;
  job->ctx = ctx;
  job->task_id = task_id;
  job->token = token;
  EnterCriticalSection(&rr->lock);
  if (rr->closing)
  {
    LeaveCriticalSection(&rr->lock);
    free(job);
    return -1;
  }
  if (rr->jobs_tail == NULL)
    rr->jobs_head = job;
  else
    rr->jobs_tail->next = job;
  rr->jobs_tail = job;
  WakeAllConditionVariable(&rr->work_cv);
  LeaveCriticalSection(&rr->lock);
  return 0;
}

void pengu_c_reactor_wake(void *r)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r != NULL)
    WSASetEvent(rr->wake_event);
}

#else /* POSIX */

#include <pthread.h>
#include <unistd.h>

#if defined(__linux__)
#include <sys/epoll.h>
#include <sys/eventfd.h>
#else
#include <poll.h>
#endif

typedef struct PenguReactorJob {
  void (*fn)(void *);
  void *ctx;
  int64_t task_id;
  int64_t token;
  struct PenguReactorJob *next;
} PenguReactorJob;

typedef struct PenguReactorDone {
  int64_t task_id;
  int64_t token;
  struct PenguReactorDone *next;
} PenguReactorDone;

struct PenguReactor {
  pthread_t owner;
  int wake_fd;
  int workers;
  int pool_started;
  int closing;

  pthread_mutex_t lock;
  pthread_cond_t work_cv;
  pthread_cond_t idle_cv;
  PenguReactorJob *jobs_head;
  PenguReactorJob *jobs_tail;
  int active_jobs;
  pthread_t *threads;

  PenguReactorDone *done_head;
  PenguReactorDone *done_tail;
  pthread_mutex_t done_lock;

#if defined(__linux__)
  int epfd;
#else
  struct pollfd *pfds;
  int64_t *ptokens;
  int pcap;
  int plen;
#endif
};

static int pengu_reactor_pool_start(PenguReactor *r);

#if defined(__linux__)
static void pengu_reactor_drain_wake(PenguReactor *r)
{
  uint64_t v;
  while (read(r->wake_fd, &v, sizeof(v)) > 0) { }
}
#else
static void pengu_reactor_drain_wake(PenguReactor *r)
{
  char buf[64];
  while (read(r->wake_fd, buf, sizeof(buf)) > 0) { }
}
#endif

static void pengu_reactor_write_wake(PenguReactor *r)
{
  if (r == NULL || r->wake_fd < 0) return;
#if defined(__linux__)
  uint64_t v = 1;
  ssize_t n = write(r->wake_fd, &v, sizeof(v));
#else
  char c = 1;
  ssize_t n = write(r->wake_fd, &c, 1);
#endif
  (void)n;
}

static void *pengu_reactor_worker(void *arg)
{
  PenguReactor *r = (PenguReactor *)arg;
  for (;;) {
    pthread_mutex_lock(&r->lock);
    while (r->jobs_head == NULL && !r->closing) {
      pthread_cond_wait(&r->work_cv, &r->lock);
    }
    if (r->jobs_head == NULL && r->closing) {
      pthread_mutex_unlock(&r->lock);
      break;
    }
    PenguReactorJob *job = r->jobs_head;
    r->jobs_head = job->next;
    if (r->jobs_head == NULL) r->jobs_tail = NULL;
    r->active_jobs++;
    pthread_mutex_unlock(&r->lock);

    job->fn(job->ctx);
    (void)pengu_c_reactor_post(r, job->task_id, job->token);

    pthread_mutex_lock(&r->lock);
    r->active_jobs--;
    if (r->active_jobs == 0 && r->jobs_head == NULL) {
      pthread_cond_broadcast(&r->idle_cv);
    }
    pthread_mutex_unlock(&r->lock);
    free(job);
  }
  return NULL;
}

static int pengu_reactor_pool_start(PenguReactor *r)
{
  if (r->pool_started) return 0;
  int n = r->workers;
  if (n <= 0) {
    long c = sysconf(_SC_NPROCESSORS_ONLN);
    n = (c > 0) ? (int)c : 4;
    if (n > 32) n = 32;
    r->workers = n;
  }
  r->threads = (pthread_t *)calloc((size_t)r->workers, sizeof(pthread_t));
  if (r->threads == NULL) return -ENOMEM;
  for (int i = 0; i < r->workers; i++) {
    if (pthread_create(&r->threads[i], NULL, pengu_reactor_worker, r) != 0) {
      r->workers = i;
      return -ENOMEM;
    }
  }
  r->pool_started = 1;
  return 0;
}

PenguReactor *pengu_c_reactor_new(int workers)
{
  PenguReactor *r = (PenguReactor *)calloc(1, sizeof(PenguReactor));
  if (r == NULL) return NULL;
  r->owner = pthread_self();
  r->workers = workers;
  r->wake_fd = -1;
  pthread_mutex_init(&r->lock, NULL);
  pthread_cond_init(&r->work_cv, NULL);
  pthread_cond_init(&r->idle_cv, NULL);
  pthread_mutex_init(&r->done_lock, NULL);
#if defined(__linux__)
  r->epfd = epoll_create1(EPOLL_CLOEXEC);
  r->wake_fd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);
  if (r->epfd < 0 || r->wake_fd < 0) {
    if (r->epfd >= 0) close(r->epfd);
    if (r->wake_fd >= 0) close(r->wake_fd);
    free(r);
    return NULL;
  }
  struct epoll_event ev;
  memset(&ev, 0, sizeof(ev));
  ev.events = EPOLLIN;
  ev.data.u64 = UINT64_MAX;
  if (epoll_ctl(r->epfd, EPOLL_CTL_ADD, r->wake_fd, &ev) != 0) {
    close(r->epfd);
    close(r->wake_fd);
    free(r);
    return NULL;
  }
#else
  int p[2];
  if (pipe(p) != 0) {
    free(r);
    return NULL;
  }
  r->wake_fd = p[0];
  r->pcap = 64;
  r->pfds = (struct pollfd *)calloc((size_t)r->pcap, sizeof(struct pollfd));
  r->ptokens = (int64_t *)calloc((size_t)r->pcap, sizeof(int64_t));
  if (r->pfds == NULL || r->ptokens == NULL) {
    close(p[0]); close(p[1]);
    free(r->pfds); free(r->ptokens); free(r);
    return NULL;
  }
  r->pfds[0].fd = p[0];
  r->pfds[0].events = POLLIN;
  r->ptokens[0] = INT64_MAX;
  r->plen = 1;
#endif
  return r;
}

int pengu_c_reactor_is_owner(void *r)
{
    PenguReactor *rr = (PenguReactor *)r;
  return r != NULL && pthread_equal(rr->owner, pthread_self());
}

int pengu_c_reactor_add(void *r, int fd, int events, int64_t token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || fd < 0) return -EINVAL;
  if (!pengu_c_reactor_is_owner(r)) return -EPERM;
#if defined(__linux__)
  struct epoll_event ev;
  memset(&ev, 0, sizeof(ev));
  if (events == 1) ev.events = EPOLLIN | EPOLLONESHOT;
  else if (events == 2) ev.events = EPOLLOUT | EPOLLONESHOT;
  else return -EINVAL;
  ev.data.u64 = (uint64_t)token;
  if (epoll_ctl(rr->epfd, EPOLL_CTL_ADD, fd, &ev) != 0) {
    return -errno;
  }
  return 0;
#else
  for (int i = 1; i < rr->plen; i++) {
    if (rr->pfds[i].fd == fd) return -EEXIST;
  }
  if (rr->plen == rr->pcap) {
    int nc = rr->pcap * 2;
    struct pollfd *np = (struct pollfd *)realloc(rr->pfds, (size_t)nc * sizeof(struct pollfd));
    if (np == NULL) return -ENOMEM;
    rr->pfds = np;
    int64_t *nt = (int64_t *)realloc(rr->ptokens, (size_t)nc * sizeof(int64_t));
    if (nt == NULL) return -ENOMEM;
    rr->ptokens = nt;
    rr->pcap = nc;
  }
  rr->pfds[rr->plen].fd = fd;
  rr->pfds[rr->plen].events = (events == 1) ? POLLIN : POLLOUT;
  rr->ptokens[rr->plen] = token;
  rr->plen++;
  return 0;
#endif
}

int pengu_c_reactor_del(void *r, int fd)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || fd < 0) return -EINVAL;
  if (!pengu_c_reactor_is_owner(r)) return -EPERM;
#if defined(__linux__)
  if (epoll_ctl(rr->epfd, EPOLL_CTL_DEL, fd, NULL) != 0) {
    if (errno == ENOENT) return 0;
    return -errno;
  }
  return 0;
#else
  for (int i = 1; i < rr->plen; i++) {
    if (rr->pfds[i].fd == fd) {
      rr->pfds[i] = rr->pfds[rr->plen - 1];
      rr->ptokens[i] = rr->ptokens[rr->plen - 1];
      rr->plen--;
      return 0;
    }
  }
  return 0;
#endif
}

int pengu_c_reactor_wait(void *r, int timeout_ms, int64_t *tokens, int cap)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || tokens == NULL || cap <= 0) return -EINVAL;
  if (!pengu_c_reactor_is_owner(r)) return -EPERM;
#if defined(__linux__)
  struct epoll_event evs[64];
  int want = cap < 64 ? cap : 64;
  int n = epoll_wait(rr->epfd, evs, want, timeout_ms);
  if (n < 0) {
    if (errno == EINTR) return 0;
    return -errno;
  }
  int out = 0;
  for (int i = 0; i < n; i++) {
    if (evs[i].data.u64 == UINT64_MAX) {
      pengu_reactor_drain_wake(r);
      continue;
    }
    tokens[out++] = (int64_t)evs[i].data.u64;
  }
  return out;
#else
  int n = poll(rr->pfds, (nfds_t)rr->plen, timeout_ms);
  if (n < 0) {
    if (errno == EINTR) return 0;
    return -errno;
  }
  if (n == 0) return 0;
  int out = 0;
  for (int i = 1; i < rr->plen && out < cap; i++) {
    if (rr->pfds[i].revents != 0) {
      tokens[out++] = rr->ptokens[i];
      rr->pfds[i] = rr->pfds[rr->plen - 1];
      rr->ptokens[i] = rr->ptokens[rr->plen - 1];
      rr->plen--;
      i--;
    }
  }
  if (rr->pfds[0].revents != 0) {
    pengu_reactor_drain_wake(r);
    rr->pfds[0].revents = 0;
  }
  return out;
#endif
}

int pengu_c_reactor_post(void *r, int64_t task_id, int64_t token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL) return -EINVAL;
  PenguReactorDone *d = (PenguReactorDone *)calloc(1, sizeof(PenguReactorDone));
  if (d == NULL) return -ENOMEM;
  d->task_id = task_id;
  d->token = token;
  pthread_mutex_lock(&rr->done_lock);
  if (rr->done_tail == NULL) rr->done_head = d;
  else rr->done_tail->next = d;
  rr->done_tail = d;
  pthread_mutex_unlock(&rr->done_lock);
  pengu_reactor_write_wake(r);
  return 0;
}

int pengu_c_reactor_take(void *r, int64_t *task_id, int64_t *token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || task_id == NULL || token == NULL) return 0;
  pthread_mutex_lock(&rr->done_lock);
  PenguReactorDone *d = rr->done_head;
  if (d != NULL) {
    rr->done_head = d->next;
    if (rr->done_head == NULL) rr->done_tail = NULL;
  }
  pthread_mutex_unlock(&rr->done_lock);
  if (d == NULL) return 0;
  *task_id = d->task_id;
  *token = d->token;
  free(d);
  return 1;
}

int64_t pengu_c_reactor_now_ms(void)
{
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (int64_t)ts.tv_sec * 1000 + (int64_t)(ts.tv_nsec / 1000000);
}

int pengu_c_reactor_offload(void *r, void (*fn)(void *), void *ctx,
                            int64_t task_id, int64_t token)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL || fn == NULL) return -EINVAL;
  if (!pengu_c_reactor_is_owner(r)) return -EPERM;
  int st = pengu_reactor_pool_start(r);
  if (st != 0) return st;
  PenguReactorJob *job = (PenguReactorJob *)calloc(1, sizeof(PenguReactorJob));
  if (job == NULL) return -ENOMEM;
  job->fn = fn;
  job->ctx = ctx;
  job->task_id = task_id;
  job->token = token;
  pthread_mutex_lock(&rr->lock);
  if (rr->closing) {
    pthread_mutex_unlock(&rr->lock);
    free(job);
    return -EPERM;
  }
  if (rr->jobs_tail == NULL) rr->jobs_head = job;
  else rr->jobs_tail->next = job;
  rr->jobs_tail = job;
  pthread_cond_signal(&rr->work_cv);
  pthread_mutex_unlock(&rr->lock);
  return 0;
}

void pengu_c_reactor_wake(void *r)
{
  pengu_reactor_write_wake(r);
}

void pengu_c_reactor_free(void *r)
{
    PenguReactor *rr = (PenguReactor *)r;
  if (r == NULL) return;
  if (!pengu_c_reactor_is_owner(r)) return;
  pthread_mutex_lock(&rr->lock);
  rr->closing = 1;
  pthread_cond_broadcast(&rr->work_cv);
  pthread_mutex_unlock(&rr->lock);
  if (rr->pool_started) {
    for (int i = 0; i < rr->workers; i++) pthread_join(rr->threads[i], NULL);
    free(rr->threads);
  }
  while (rr->jobs_head != NULL) {
    PenguReactorJob *j = rr->jobs_head;
    rr->jobs_head = j->next;
    free(j);
  }
  while (rr->done_head != NULL) {
    PenguReactorDone *d = rr->done_head;
    rr->done_head = d->next;
    free(d);
  }
#if defined(__linux__)
  if (rr->epfd >= 0) close(rr->epfd);
#else
  free(rr->pfds);
  free(rr->ptokens);
#endif
  if (rr->wake_fd >= 0) close(rr->wake_fd);
  pthread_mutex_destroy(&rr->lock);
  pthread_mutex_destroy(&rr->done_lock);
  pthread_cond_destroy(&rr->work_cv);
  pthread_cond_destroy(&rr->idle_cv);
  free(r);
}

#endif /* _WIN32 */
