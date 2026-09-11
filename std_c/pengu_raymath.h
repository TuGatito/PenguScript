/* std_c/pengu_raymath.h
 * Companion header for std_c/wrappers_raymath.c: extern prototypes of the
 * raymath functions with a pengu_rm_ prefix for PenguScript std/raymath bindings.
 * Staged to build/include/ by build_runtime.build_raymath().
 */
#ifndef PENGU_RAYMATH_H
#define PENGU_RAYMATH_H

#include "raylib.h"

#ifdef __cplusplus
extern "C" {
#endif

#ifndef RAYMATH_H
typedef struct float3 {
    float v[3];
} float3;

typedef struct float16 {
    float v[16];
} float16;
#endif

float pengu_rm_Clamp(float value, float min, float max);
float pengu_rm_Lerp(float start, float end, float amount);
float pengu_rm_Normalize(float value, float start, float end);
float pengu_rm_Remap(float value, float inputStart, float inputEnd, float outputStart, float outputEnd);
float pengu_rm_Wrap(float value, float min, float max);
int pengu_rm_FloatEquals(float x, float y);
Vector2 pengu_rm_Vector2Zero(void);
Vector2 pengu_rm_Vector2One(void);
Vector2 pengu_rm_Vector2Add(Vector2 v1, Vector2 v2);
Vector2 pengu_rm_Vector2AddValue(Vector2 v, float add);
Vector2 pengu_rm_Vector2Subtract(Vector2 v1, Vector2 v2);
Vector2 pengu_rm_Vector2SubtractValue(Vector2 v, float sub);
float pengu_rm_Vector2Length(Vector2 v);
float pengu_rm_Vector2LengthSqr(Vector2 v);
float pengu_rm_Vector2DotProduct(Vector2 v1, Vector2 v2);
float pengu_rm_Vector2CrossProduct(Vector2 v1, Vector2 v2);
float pengu_rm_Vector2Distance(Vector2 v1, Vector2 v2);
float pengu_rm_Vector2DistanceSqr(Vector2 v1, Vector2 v2);
float pengu_rm_Vector2Angle(Vector2 v1, Vector2 v2);
float pengu_rm_Vector2LineAngle(Vector2 start, Vector2 end);
Vector2 pengu_rm_Vector2Scale(Vector2 v, float scale);
Vector2 pengu_rm_Vector2Multiply(Vector2 v1, Vector2 v2);
Vector2 pengu_rm_Vector2Negate(Vector2 v);
Vector2 pengu_rm_Vector2Divide(Vector2 v1, Vector2 v2);
Vector2 pengu_rm_Vector2Normalize(Vector2 v);
Vector2 pengu_rm_Vector2Transform(Vector2 v, Matrix mat);
Vector2 pengu_rm_Vector2Lerp(Vector2 v1, Vector2 v2, float amount);
Vector2 pengu_rm_Vector2Reflect(Vector2 v, Vector2 normal);
Vector2 pengu_rm_Vector2Min(Vector2 v1, Vector2 v2);
Vector2 pengu_rm_Vector2Max(Vector2 v1, Vector2 v2);
Vector2 pengu_rm_Vector2Rotate(Vector2 v, float angle);
Vector2 pengu_rm_Vector2MoveTowards(Vector2 v, Vector2 target, float maxDistance);
Vector2 pengu_rm_Vector2Invert(Vector2 v);
Vector2 pengu_rm_Vector2Clamp(Vector2 v, Vector2 min, Vector2 max);
Vector2 pengu_rm_Vector2ClampValue(Vector2 v, float min, float max);
int pengu_rm_Vector2Equals(Vector2 p, Vector2 q);
Vector2 pengu_rm_Vector2Refract(Vector2 v, Vector2 n, float r);
Vector3 pengu_rm_Vector3Zero(void);
Vector3 pengu_rm_Vector3One(void);
Vector3 pengu_rm_Vector3Add(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3AddValue(Vector3 v, float add);
Vector3 pengu_rm_Vector3Subtract(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3SubtractValue(Vector3 v, float sub);
Vector3 pengu_rm_Vector3Scale(Vector3 v, float scalar);
Vector3 pengu_rm_Vector3Multiply(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3CrossProduct(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3Perpendicular(Vector3 v);
float pengu_rm_Vector3Length(const Vector3 v);
float pengu_rm_Vector3LengthSqr(const Vector3 v);
float pengu_rm_Vector3DotProduct(Vector3 v1, Vector3 v2);
float pengu_rm_Vector3Distance(Vector3 v1, Vector3 v2);
float pengu_rm_Vector3DistanceSqr(Vector3 v1, Vector3 v2);
float pengu_rm_Vector3Angle(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3Negate(Vector3 v);
Vector3 pengu_rm_Vector3Divide(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3Normalize(Vector3 v);
Vector3 pengu_rm_Vector3Project(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3Reject(Vector3 v1, Vector3 v2);
void pengu_rm_Vector3OrthoNormalize(Vector3 *v1, Vector3 *v2);
Vector3 pengu_rm_Vector3Transform(Vector3 v, Matrix mat);
Vector3 pengu_rm_Vector3RotateByQuaternion(Vector3 v, Quaternion q);
Vector3 pengu_rm_Vector3RotateByAxisAngle(Vector3 v, Vector3 axis, float angle);
Vector3 pengu_rm_Vector3MoveTowards(Vector3 v, Vector3 target, float maxDistance);
Vector3 pengu_rm_Vector3Lerp(Vector3 v1, Vector3 v2, float amount);
Vector3 pengu_rm_Vector3CubicHermite(Vector3 v1, Vector3 tangent1, Vector3 v2, Vector3 tangent2, float amount);
Vector3 pengu_rm_Vector3Reflect(Vector3 v, Vector3 normal);
Vector3 pengu_rm_Vector3Min(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3Max(Vector3 v1, Vector3 v2);
Vector3 pengu_rm_Vector3Barycenter(Vector3 p, Vector3 a, Vector3 b, Vector3 c);
Vector3 pengu_rm_Vector3Unproject(Vector3 source, Matrix projection, Matrix view);
float3 pengu_rm_Vector3ToFloatV(Vector3 v);
Vector3 pengu_rm_Vector3Invert(Vector3 v);
Vector3 pengu_rm_Vector3Clamp(Vector3 v, Vector3 min, Vector3 max);
Vector3 pengu_rm_Vector3ClampValue(Vector3 v, float min, float max);
int pengu_rm_Vector3Equals(Vector3 p, Vector3 q);
Vector3 pengu_rm_Vector3Refract(Vector3 v, Vector3 n, float r);
Vector4 pengu_rm_Vector4Zero(void);
Vector4 pengu_rm_Vector4One(void);
Vector4 pengu_rm_Vector4Add(Vector4 v1, Vector4 v2);
Vector4 pengu_rm_Vector4AddValue(Vector4 v, float add);
Vector4 pengu_rm_Vector4Subtract(Vector4 v1, Vector4 v2);
Vector4 pengu_rm_Vector4SubtractValue(Vector4 v, float add);
float pengu_rm_Vector4Length(Vector4 v);
float pengu_rm_Vector4LengthSqr(Vector4 v);
float pengu_rm_Vector4DotProduct(Vector4 v1, Vector4 v2);
float pengu_rm_Vector4Distance(Vector4 v1, Vector4 v2);
float pengu_rm_Vector4DistanceSqr(Vector4 v1, Vector4 v2);
Vector4 pengu_rm_Vector4Scale(Vector4 v, float scale);
Vector4 pengu_rm_Vector4Multiply(Vector4 v1, Vector4 v2);
Vector4 pengu_rm_Vector4Negate(Vector4 v);
Vector4 pengu_rm_Vector4Divide(Vector4 v1, Vector4 v2);
Vector4 pengu_rm_Vector4Normalize(Vector4 v);
Vector4 pengu_rm_Vector4Min(Vector4 v1, Vector4 v2);
Vector4 pengu_rm_Vector4Max(Vector4 v1, Vector4 v2);
Vector4 pengu_rm_Vector4Lerp(Vector4 v1, Vector4 v2, float amount);
Vector4 pengu_rm_Vector4MoveTowards(Vector4 v, Vector4 target, float maxDistance);
Vector4 pengu_rm_Vector4Invert(Vector4 v);
int pengu_rm_Vector4Equals(Vector4 p, Vector4 q);
float pengu_rm_MatrixDeterminant(Matrix mat);
float pengu_rm_MatrixTrace(Matrix mat);
Matrix pengu_rm_MatrixTranspose(Matrix mat);
Matrix pengu_rm_MatrixInvert(Matrix mat);
Matrix pengu_rm_MatrixIdentity(void);
Matrix pengu_rm_MatrixAdd(Matrix left, Matrix right);
Matrix pengu_rm_MatrixSubtract(Matrix left, Matrix right);
Matrix pengu_rm_MatrixMultiply(Matrix left, Matrix right);
Matrix pengu_rm_MatrixMultiplyValue(Matrix left, float value);
Matrix pengu_rm_MatrixTranslate(float x, float y, float z);
Matrix pengu_rm_MatrixRotate(Vector3 axis, float angle);
Matrix pengu_rm_MatrixRotateX(float angle);
Matrix pengu_rm_MatrixRotateY(float angle);
Matrix pengu_rm_MatrixRotateZ(float angle);
Matrix pengu_rm_MatrixRotateXYZ(Vector3 angle);
Matrix pengu_rm_MatrixRotateZYX(Vector3 angle);
Matrix pengu_rm_MatrixScale(float x, float y, float z);
Matrix pengu_rm_MatrixFrustum(double left, double right, double bottom, double top, double nearPlane, double farPlane);
Matrix pengu_rm_MatrixPerspective(double fovY, double aspect, double nearPlane, double farPlane);
Matrix pengu_rm_MatrixOrtho(double left, double right, double bottom, double top, double nearPlane, double farPlane);
Matrix pengu_rm_MatrixLookAt(Vector3 eye, Vector3 target, Vector3 up);
float16 pengu_rm_MatrixToFloatV(Matrix mat);
Quaternion pengu_rm_QuaternionAdd(Quaternion q1, Quaternion q2);
Quaternion pengu_rm_QuaternionAddValue(Quaternion q, float add);
Quaternion pengu_rm_QuaternionSubtract(Quaternion q1, Quaternion q2);
Quaternion pengu_rm_QuaternionSubtractValue(Quaternion q, float sub);
Quaternion pengu_rm_QuaternionIdentity(void);
float pengu_rm_QuaternionLength(Quaternion q);
Quaternion pengu_rm_QuaternionNormalize(Quaternion q);
Quaternion pengu_rm_QuaternionInvert(Quaternion q);
Quaternion pengu_rm_QuaternionMultiply(Quaternion q1, Quaternion q2);
Quaternion pengu_rm_QuaternionScale(Quaternion q, float mul);
Quaternion pengu_rm_QuaternionDivide(Quaternion q1, Quaternion q2);
Quaternion pengu_rm_QuaternionLerp(Quaternion q1, Quaternion q2, float amount);
Quaternion pengu_rm_QuaternionNlerp(Quaternion q1, Quaternion q2, float amount);
Quaternion pengu_rm_QuaternionSlerp(Quaternion q1, Quaternion q2, float amount);
Quaternion pengu_rm_QuaternionCubicHermiteSpline(Quaternion q1, Quaternion outTangent1, Quaternion q2, Quaternion inTangent2, float t);
Quaternion pengu_rm_QuaternionFromVector3ToVector3(Vector3 from, Vector3 to);
Quaternion pengu_rm_QuaternionFromMatrix(Matrix mat);
Matrix pengu_rm_QuaternionToMatrix(Quaternion q);
Quaternion pengu_rm_QuaternionFromAxisAngle(Vector3 axis, float angle);
void pengu_rm_QuaternionToAxisAngle(Quaternion q, Vector3 *outAxis, float *outAngle);
Quaternion pengu_rm_QuaternionFromEuler(float pitch, float yaw, float roll);
Vector3 pengu_rm_QuaternionToEuler(Quaternion q);
Quaternion pengu_rm_QuaternionTransform(Quaternion q, Matrix mat);
int pengu_rm_QuaternionEquals(Quaternion p, Quaternion q);
Matrix pengu_rm_MatrixCompose(Vector3 translation, Quaternion rotation, Vector3 scale);
void pengu_rm_MatrixDecompose(Matrix mat, Vector3 *translation, Quaternion *rotation, Vector3 *scale);

#ifdef __cplusplus
}
#endif

#endif /* PENGU_RAYMATH_H */
