/* pengu_reactor.c — explicit user-space reactor for std.reactor.
 *
 * The C half only moves readiness and work tokens; the scheduling policy
 * (tasks, timers, what to resume) lives in std/reactor.pengu.  Linux uses
 * epoll + eventfd; other POSIX systems use poll + a self-pipe.  Windows has a
 * documented stub in 0.35 (std.reactor.new panics there).
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

#ifndef ENOSYS
#define ENOSYS 38
#endif

PenguReactor *pengu_c_reactor_new(int workers) { (void)workers; return NULL; }
int pengu_c_reactor_is_owner(PenguReactor *r) { (void)r; return 0; }
void pengu_c_reactor_free(PenguReactor *r) { (void)r; }
int pengu_c_reactor_add(PenguReactor *r, int fd, int events, int64_t token)
{ (void)r; (void)fd; (void)events; (void)token; return -ENOSYS; }
int pengu_c_reactor_del(PenguReactor *r, int fd) { (void)r; (void)fd; return -ENOSYS; }
int pengu_c_reactor_wait(PenguReactor *r, int timeout_ms, int64_t *tokens, int cap)
{ (void)r; (void)timeout_ms; (void)tokens; (void)cap; return -ENOSYS; }
int pengu_c_reactor_post(PenguReactor *r, int64_t task_id, int64_t token)
{ (void)r; (void)task_id; (void)token; return -ENOSYS; }
int pengu_c_reactor_take(PenguReactor *r, int64_t *task_id, int64_t *token)
{ (void)r; (void)task_id; (void)token; return 0; }
int64_t pengu_c_reactor_now_ms(void) { return 0; }
int pengu_c_reactor_offload(PenguReactor *r, void (*fn)(void *), void *ctx,
                            int64_t task_id, int64_t token)
{ (void)r; (void)fn; (void)ctx; (void)task_id; (void)token; return -ENOSYS; }
void pengu_c_reactor_wake(PenguReactor *r) { (void)r; }

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

int pengu_c_reactor_is_owner(PenguReactor *r)
{
  return r != NULL && pthread_equal(r->owner, pthread_self());
}

int pengu_c_reactor_add(PenguReactor *r, int fd, int events, int64_t token)
{
  if (r == NULL || fd < 0) return -EINVAL;
  if (!pengu_c_reactor_is_owner(r)) return -EPERM;
#if defined(__linux__)
  struct epoll_event ev;
  memset(&ev, 0, sizeof(ev));
  if (events == 1) ev.events = EPOLLIN | EPOLLONESHOT;
  else if (events == 2) ev.events = EPOLLOUT | EPOLLONESHOT;
  else return -EINVAL;
  ev.data.u64 = (uint64_t)token;
  if (epoll_ctl(r->epfd, EPOLL_CTL_ADD, fd, &ev) != 0) {
    return -errno;
  }
  return 0;
#else
  for (int i = 1; i < r->plen; i++) {
    if (r->pfds[i].fd == fd) return -EEXIST;
  }
  if (r->plen == r->pcap) {
    int nc = r->pcap * 2;
    struct pollfd *np = (struct pollfd *)realloc(r->pfds, (size_t)nc * sizeof(struct pollfd));
    if (np == NULL) return -ENOMEM;
    r->pfds = np;
    int64_t *nt = (int64_t *)realloc(r->ptokens, (size_t)nc * sizeof(int64_t));
    if (nt == NULL) return -ENOMEM;
    r->ptokens = nt;
    r->pcap = nc;
  }
  r->pfds[r->plen].fd = fd;
  r->pfds[r->plen].events = (events == 1) ? POLLIN : POLLOUT;
  r->ptokens[r->plen] = token;
  r->plen++;
  return 0;
#endif
}

int pengu_c_reactor_del(PenguReactor *r, int fd)
{
  if (r == NULL || fd < 0) return -EINVAL;
  if (!pengu_c_reactor_is_owner(r)) return -EPERM;
#if defined(__linux__)
  if (epoll_ctl(r->epfd, EPOLL_CTL_DEL, fd, NULL) != 0) {
    if (errno == ENOENT) return 0;
    return -errno;
  }
  return 0;
#else
  for (int i = 1; i < r->plen; i++) {
    if (r->pfds[i].fd == fd) {
      r->pfds[i] = r->pfds[r->plen - 1];
      r->ptokens[i] = r->ptokens[r->plen - 1];
      r->plen--;
      return 0;
    }
  }
  return 0;
#endif
}

int pengu_c_reactor_wait(PenguReactor *r, int timeout_ms, int64_t *tokens, int cap)
{
  if (r == NULL || tokens == NULL || cap <= 0) return -EINVAL;
  if (!pengu_c_reactor_is_owner(r)) return -EPERM;
#if defined(__linux__)
  struct epoll_event evs[64];
  int want = cap < 64 ? cap : 64;
  int n = epoll_wait(r->epfd, evs, want, timeout_ms);
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
  int n = poll(r->pfds, (nfds_t)r->plen, timeout_ms);
  if (n < 0) {
    if (errno == EINTR) return 0;
    return -errno;
  }
  if (n == 0) return 0;
  int out = 0;
  for (int i = 1; i < r->plen && out < cap; i++) {
    if (r->pfds[i].revents != 0) {
      tokens[out++] = r->ptokens[i];
      r->pfds[i] = r->pfds[r->plen - 1];
      r->ptokens[i] = r->ptokens[r->plen - 1];
      r->plen--;
      i--;
    }
  }
  if (r->pfds[0].revents != 0) {
    pengu_reactor_drain_wake(r);
    r->pfds[0].revents = 0;
  }
  return out;
#endif
}

int pengu_c_reactor_post(PenguReactor *r, int64_t task_id, int64_t token)
{
  if (r == NULL) return -EINVAL;
  PenguReactorDone *d = (PenguReactorDone *)calloc(1, sizeof(PenguReactorDone));
  if (d == NULL) return -ENOMEM;
  d->task_id = task_id;
  d->token = token;
  pthread_mutex_lock(&r->done_lock);
  if (r->done_tail == NULL) r->done_head = d;
  else r->done_tail->next = d;
  r->done_tail = d;
  pthread_mutex_unlock(&r->done_lock);
  pengu_reactor_write_wake(r);
  return 0;
}

int pengu_c_reactor_take(PenguReactor *r, int64_t *task_id, int64_t *token)
{
  if (r == NULL || task_id == NULL || token == NULL) return 0;
  pthread_mutex_lock(&r->done_lock);
  PenguReactorDone *d = r->done_head;
  if (d != NULL) {
    r->done_head = d->next;
    if (r->done_head == NULL) r->done_tail = NULL;
  }
  pthread_mutex_unlock(&r->done_lock);
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

int pengu_c_reactor_offload(PenguReactor *r, void (*fn)(void *), void *ctx,
                            int64_t task_id, int64_t token)
{
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
  pthread_mutex_lock(&r->lock);
  if (r->closing) {
    pthread_mutex_unlock(&r->lock);
    free(job);
    return -EPERM;
  }
  if (r->jobs_tail == NULL) r->jobs_head = job;
  else r->jobs_tail->next = job;
  r->jobs_tail = job;
  pthread_cond_signal(&r->work_cv);
  pthread_mutex_unlock(&r->lock);
  return 0;
}

void pengu_c_reactor_wake(PenguReactor *r)
{
  pengu_reactor_write_wake(r);
}

void pengu_c_reactor_free(PenguReactor *r)
{
  if (r == NULL) return;
  if (!pengu_c_reactor_is_owner(r)) return;
  pthread_mutex_lock(&r->lock);
  r->closing = 1;
  pthread_cond_broadcast(&r->work_cv);
  pthread_mutex_unlock(&r->lock);
  if (r->pool_started) {
    for (int i = 0; i < r->workers; i++) pthread_join(r->threads[i], NULL);
    free(r->threads);
  }
  while (r->jobs_head != NULL) {
    PenguReactorJob *j = r->jobs_head;
    r->jobs_head = j->next;
    free(j);
  }
  while (r->done_head != NULL) {
    PenguReactorDone *d = r->done_head;
    r->done_head = d->next;
    free(d);
  }
#if defined(__linux__)
  if (r->epfd >= 0) close(r->epfd);
#else
  free(r->pfds);
  free(r->ptokens);
#endif
  if (r->wake_fd >= 0) close(r->wake_fd);
  pthread_mutex_destroy(&r->lock);
  pthread_mutex_destroy(&r->done_lock);
  pthread_cond_destroy(&r->work_cv);
  pthread_cond_destroy(&r->idle_cv);
  free(r);
}

#endif /* _WIN32 */
