/* std_c/wrappers_raymath.c
 * Non-inline wrappers for raymath inline functions.
 * Compiled into build/lib/libpengu_raymath.a by build_runtime.build_raymath().
 */
#include "raylib.h"
#include "raylib/raymath.h"
#include "pengu_raymath.h"

float pengu_rm_Clamp(float value, float min, float max) { return Clamp(value, min, max); }
float pengu_rm_Lerp(float start, float end, float amount) { return Lerp(start, end, amount); }
float pengu_rm_Normalize(float value, float start, float end) { return Normalize(value, start, end); }
float pengu_rm_Remap(float value, float inputStart, float inputEnd, float outputStart, float outputEnd) { return Remap(value, inputStart, inputEnd, outputStart, outputEnd); }
float pengu_rm_Wrap(float value, float min, float max) { return Wrap(value, min, max); }
int pengu_rm_FloatEquals(float x, float y) { return FloatEquals(x, y); }
Vector2 pengu_rm_Vector2Zero(void) { return Vector2Zero(); }
Vector2 pengu_rm_Vector2One(void) { return Vector2One(); }
Vector2 pengu_rm_Vector2Add(Vector2 v1, Vector2 v2) { return Vector2Add(v1, v2); }
Vector2 pengu_rm_Vector2AddValue(Vector2 v, float add) { return Vector2AddValue(v, add); }
Vector2 pengu_rm_Vector2Subtract(Vector2 v1, Vector2 v2) { return Vector2Subtract(v1, v2); }
Vector2 pengu_rm_Vector2SubtractValue(Vector2 v, float sub) { return Vector2SubtractValue(v, sub); }
float pengu_rm_Vector2Length(Vector2 v) { return Vector2Length(v); }
float pengu_rm_Vector2LengthSqr(Vector2 v) { return Vector2LengthSqr(v); }
float pengu_rm_Vector2DotProduct(Vector2 v1, Vector2 v2) { return Vector2DotProduct(v1, v2); }
float pengu_rm_Vector2CrossProduct(Vector2 v1, Vector2 v2) { return Vector2CrossProduct(v1, v2); }
float pengu_rm_Vector2Distance(Vector2 v1, Vector2 v2) { return Vector2Distance(v1, v2); }
float pengu_rm_Vector2DistanceSqr(Vector2 v1, Vector2 v2) { return Vector2DistanceSqr(v1, v2); }
float pengu_rm_Vector2Angle(Vector2 v1, Vector2 v2) { return Vector2Angle(v1, v2); }
float pengu_rm_Vector2LineAngle(Vector2 start, Vector2 end) { return Vector2LineAngle(start, end); }
Vector2 pengu_rm_Vector2Scale(Vector2 v, float scale) { return Vector2Scale(v, scale); }
Vector2 pengu_rm_Vector2Multiply(Vector2 v1, Vector2 v2) { return Vector2Multiply(v1, v2); }
Vector2 pengu_rm_Vector2Negate(Vector2 v) { return Vector2Negate(v); }
Vector2 pengu_rm_Vector2Divide(Vector2 v1, Vector2 v2) { return Vector2Divide(v1, v2); }
Vector2 pengu_rm_Vector2Normalize(Vector2 v) { return Vector2Normalize(v); }
Vector2 pengu_rm_Vector2Transform(Vector2 v, Matrix mat) { return Vector2Transform(v, mat); }
Vector2 pengu_rm_Vector2Lerp(Vector2 v1, Vector2 v2, float amount) { return Vector2Lerp(v1, v2, amount); }
Vector2 pengu_rm_Vector2Reflect(Vector2 v, Vector2 normal) { return Vector2Reflect(v, normal); }
Vector2 pengu_rm_Vector2Min(Vector2 v1, Vector2 v2) { return Vector2Min(v1, v2); }
Vector2 pengu_rm_Vector2Max(Vector2 v1, Vector2 v2) { return Vector2Max(v1, v2); }
Vector2 pengu_rm_Vector2Rotate(Vector2 v, float angle) { return Vector2Rotate(v, angle); }
Vector2 pengu_rm_Vector2MoveTowards(Vector2 v, Vector2 target, float maxDistance) { return Vector2MoveTowards(v, target, maxDistance); }
Vector2 pengu_rm_Vector2Invert(Vector2 v) { return Vector2Invert(v); }
Vector2 pengu_rm_Vector2Clamp(Vector2 v, Vector2 min, Vector2 max) { return Vector2Clamp(v, min, max); }
Vector2 pengu_rm_Vector2ClampValue(Vector2 v, float min, float max) { return Vector2ClampValue(v, min, max); }
int pengu_rm_Vector2Equals(Vector2 p, Vector2 q) { return Vector2Equals(p, q); }
Vector2 pengu_rm_Vector2Refract(Vector2 v, Vector2 n, float r) { return Vector2Refract(v, n, r); }
Vector3 pengu_rm_Vector3Zero(void) { return Vector3Zero(); }
Vector3 pengu_rm_Vector3One(void) { return Vector3One(); }
Vector3 pengu_rm_Vector3Add(Vector3 v1, Vector3 v2) { return Vector3Add(v1, v2); }
Vector3 pengu_rm_Vector3AddValue(Vector3 v, float add) { return Vector3AddValue(v, add); }
Vector3 pengu_rm_Vector3Subtract(Vector3 v1, Vector3 v2) { return Vector3Subtract(v1, v2); }
Vector3 pengu_rm_Vector3SubtractValue(Vector3 v, float sub) { return Vector3SubtractValue(v, sub); }
Vector3 pengu_rm_Vector3Scale(Vector3 v, float scalar) { return Vector3Scale(v, scalar); }
Vector3 pengu_rm_Vector3Multiply(Vector3 v1, Vector3 v2) { return Vector3Multiply(v1, v2); }
Vector3 pengu_rm_Vector3CrossProduct(Vector3 v1, Vector3 v2) { return Vector3CrossProduct(v1, v2); }
Vector3 pengu_rm_Vector3Perpendicular(Vector3 v) { return Vector3Perpendicular(v); }
float pengu_rm_Vector3Length(const Vector3 v) { return Vector3Length(v); }
float pengu_rm_Vector3LengthSqr(const Vector3 v) { return Vector3LengthSqr(v); }
float pengu_rm_Vector3DotProduct(Vector3 v1, Vector3 v2) { return Vector3DotProduct(v1, v2); }
float pengu_rm_Vector3Distance(Vector3 v1, Vector3 v2) { return Vector3Distance(v1, v2); }
float pengu_rm_Vector3DistanceSqr(Vector3 v1, Vector3 v2) { return Vector3DistanceSqr(v1, v2); }
float pengu_rm_Vector3Angle(Vector3 v1, Vector3 v2) { return Vector3Angle(v1, v2); }
Vector3 pengu_rm_Vector3Negate(Vector3 v) { return Vector3Negate(v); }
Vector3 pengu_rm_Vector3Divide(Vector3 v1, Vector3 v2) { return Vector3Divide(v1, v2); }
Vector3 pengu_rm_Vector3Normalize(Vector3 v) { return Vector3Normalize(v); }
Vector3 pengu_rm_Vector3Project(Vector3 v1, Vector3 v2) { return Vector3Project(v1, v2); }
Vector3 pengu_rm_Vector3Reject(Vector3 v1, Vector3 v2) { return Vector3Reject(v1, v2); }
void pengu_rm_Vector3OrthoNormalize(Vector3 *v1, Vector3 *v2) { Vector3OrthoNormalize(v1, v2); }
Vector3 pengu_rm_Vector3Transform(Vector3 v, Matrix mat) { return Vector3Transform(v, mat); }
Vector3 pengu_rm_Vector3RotateByQuaternion(Vector3 v, Quaternion q) { return Vector3RotateByQuaternion(v, q); }
Vector3 pengu_rm_Vector3RotateByAxisAngle(Vector3 v, Vector3 axis, float angle) { return Vector3RotateByAxisAngle(v, axis, angle); }
Vector3 pengu_rm_Vector3MoveTowards(Vector3 v, Vector3 target, float maxDistance) { return Vector3MoveTowards(v, target, maxDistance); }
Vector3 pengu_rm_Vector3Lerp(Vector3 v1, Vector3 v2, float amount) { return Vector3Lerp(v1, v2, amount); }
Vector3 pengu_rm_Vector3CubicHermite(Vector3 v1, Vector3 tangent1, Vector3 v2, Vector3 tangent2, float amount) { return Vector3CubicHermite(v1, tangent1, v2, tangent2, amount); }
Vector3 pengu_rm_Vector3Reflect(Vector3 v, Vector3 normal) { return Vector3Reflect(v, normal); }
Vector3 pengu_rm_Vector3Min(Vector3 v1, Vector3 v2) { return Vector3Min(v1, v2); }
Vector3 pengu_rm_Vector3Max(Vector3 v1, Vector3 v2) { return Vector3Max(v1, v2); }
Vector3 pengu_rm_Vector3Barycenter(Vector3 p, Vector3 a, Vector3 b, Vector3 c) { return Vector3Barycenter(p, a, b, c); }
Vector3 pengu_rm_Vector3Unproject(Vector3 source, Matrix projection, Matrix view) { return Vector3Unproject(source, projection, view); }
float3 pengu_rm_Vector3ToFloatV(Vector3 v) { return Vector3ToFloatV(v); }
Vector3 pengu_rm_Vector3Invert(Vector3 v) { return Vector3Invert(v); }
Vector3 pengu_rm_Vector3Clamp(Vector3 v, Vector3 min, Vector3 max) { return Vector3Clamp(v, min, max); }
Vector3 pengu_rm_Vector3ClampValue(Vector3 v, float min, float max) { return Vector3ClampValue(v, min, max); }
int pengu_rm_Vector3Equals(Vector3 p, Vector3 q) { return Vector3Equals(p, q); }
Vector3 pengu_rm_Vector3Refract(Vector3 v, Vector3 n, float r) { return Vector3Refract(v, n, r); }
Vector4 pengu_rm_Vector4Zero(void) { return Vector4Zero(); }
Vector4 pengu_rm_Vector4One(void) { return Vector4One(); }
Vector4 pengu_rm_Vector4Add(Vector4 v1, Vector4 v2) { return Vector4Add(v1, v2); }
Vector4 pengu_rm_Vector4AddValue(Vector4 v, float add) { return Vector4AddValue(v, add); }
Vector4 pengu_rm_Vector4Subtract(Vector4 v1, Vector4 v2) { return Vector4Subtract(v1, v2); }
Vector4 pengu_rm_Vector4SubtractValue(Vector4 v, float add) { return Vector4SubtractValue(v, add); }
float pengu_rm_Vector4Length(Vector4 v) { return Vector4Length(v); }
float pengu_rm_Vector4LengthSqr(Vector4 v) { return Vector4LengthSqr(v); }
float pengu_rm_Vector4DotProduct(Vector4 v1, Vector4 v2) { return Vector4DotProduct(v1, v2); }
float pengu_rm_Vector4Distance(Vector4 v1, Vector4 v2) { return Vector4Distance(v1, v2); }
float pengu_rm_Vector4DistanceSqr(Vector4 v1, Vector4 v2) { return Vector4DistanceSqr(v1, v2); }
Vector4 pengu_rm_Vector4Scale(Vector4 v, float scale) { return Vector4Scale(v, scale); }
Vector4 pengu_rm_Vector4Multiply(Vector4 v1, Vector4 v2) { return Vector4Multiply(v1, v2); }
Vector4 pengu_rm_Vector4Negate(Vector4 v) { return Vector4Negate(v); }
Vector4 pengu_rm_Vector4Divide(Vector4 v1, Vector4 v2) { return Vector4Divide(v1, v2); }
Vector4 pengu_rm_Vector4Normalize(Vector4 v) { return Vector4Normalize(v); }
Vector4 pengu_rm_Vector4Min(Vector4 v1, Vector4 v2) { return Vector4Min(v1, v2); }
Vector4 pengu_rm_Vector4Max(Vector4 v1, Vector4 v2) { return Vector4Max(v1, v2); }
Vector4 pengu_rm_Vector4Lerp(Vector4 v1, Vector4 v2, float amount) { return Vector4Lerp(v1, v2, amount); }
Vector4 pengu_rm_Vector4MoveTowards(Vector4 v, Vector4 target, float maxDistance) { return Vector4MoveTowards(v, target, maxDistance); }
Vector4 pengu_rm_Vector4Invert(Vector4 v) { return Vector4Invert(v); }
int pengu_rm_Vector4Equals(Vector4 p, Vector4 q) { return Vector4Equals(p, q); }
float pengu_rm_MatrixDeterminant(Matrix mat) { return MatrixDeterminant(mat); }
float pengu_rm_MatrixTrace(Matrix mat) { return MatrixTrace(mat); }
Matrix pengu_rm_MatrixTranspose(Matrix mat) { return MatrixTranspose(mat); }
Matrix pengu_rm_MatrixInvert(Matrix mat) { return MatrixInvert(mat); }
Matrix pengu_rm_MatrixIdentity(void) { return MatrixIdentity(); }
Matrix pengu_rm_MatrixAdd(Matrix left, Matrix right) { return MatrixAdd(left, right); }
Matrix pengu_rm_MatrixSubtract(Matrix left, Matrix right) { return MatrixSubtract(left, right); }
Matrix pengu_rm_MatrixMultiply(Matrix left, Matrix right) { return MatrixMultiply(left, right); }
Matrix pengu_rm_MatrixMultiplyValue(Matrix left, float value) { return MatrixMultiplyValue(left, value); }
Matrix pengu_rm_MatrixTranslate(float x, float y, float z) { return MatrixTranslate(x, y, z); }
Matrix pengu_rm_MatrixRotate(Vector3 axis, float angle) { return MatrixRotate(axis, angle); }
Matrix pengu_rm_MatrixRotateX(float angle) { return MatrixRotateX(angle); }
Matrix pengu_rm_MatrixRotateY(float angle) { return MatrixRotateY(angle); }
Matrix pengu_rm_MatrixRotateZ(float angle) { return MatrixRotateZ(angle); }
Matrix pengu_rm_MatrixRotateXYZ(Vector3 angle) { return MatrixRotateXYZ(angle); }
Matrix pengu_rm_MatrixRotateZYX(Vector3 angle) { return MatrixRotateZYX(angle); }
Matrix pengu_rm_MatrixScale(float x, float y, float z) { return MatrixScale(x, y, z); }
Matrix pengu_rm_MatrixFrustum(double left, double right, double bottom, double top, double nearPlane, double farPlane) { return MatrixFrustum(left, right, bottom, top, nearPlane, farPlane); }
Matrix pengu_rm_MatrixPerspective(double fovY, double aspect, double nearPlane, double farPlane) { return MatrixPerspective(fovY, aspect, nearPlane, farPlane); }
Matrix pengu_rm_MatrixOrtho(double left, double right, double bottom, double top, double nearPlane, double farPlane) { return MatrixOrtho(left, right, bottom, top, nearPlane, farPlane); }
Matrix pengu_rm_MatrixLookAt(Vector3 eye, Vector3 target, Vector3 up) { return MatrixLookAt(eye, target, up); }
float16 pengu_rm_MatrixToFloatV(Matrix mat) { return MatrixToFloatV(mat); }
Quaternion pengu_rm_QuaternionAdd(Quaternion q1, Quaternion q2) { return QuaternionAdd(q1, q2); }
Quaternion pengu_rm_QuaternionAddValue(Quaternion q, float add) { return QuaternionAddValue(q, add); }
Quaternion pengu_rm_QuaternionSubtract(Quaternion q1, Quaternion q2) { return QuaternionSubtract(q1, q2); }
Quaternion pengu_rm_QuaternionSubtractValue(Quaternion q, float sub) { return QuaternionSubtractValue(q, sub); }
Quaternion pengu_rm_QuaternionIdentity(void) { return QuaternionIdentity(); }
float pengu_rm_QuaternionLength(Quaternion q) { return QuaternionLength(q); }
Quaternion pengu_rm_QuaternionNormalize(Quaternion q) { return QuaternionNormalize(q); }
Quaternion pengu_rm_QuaternionInvert(Quaternion q) { return QuaternionInvert(q); }
Quaternion pengu_rm_QuaternionMultiply(Quaternion q1, Quaternion q2) { return QuaternionMultiply(q1, q2); }
Quaternion pengu_rm_QuaternionScale(Quaternion q, float mul) { return QuaternionScale(q, mul); }
Quaternion pengu_rm_QuaternionDivide(Quaternion q1, Quaternion q2) { return QuaternionDivide(q1, q2); }
Quaternion pengu_rm_QuaternionLerp(Quaternion q1, Quaternion q2, float amount) { return QuaternionLerp(q1, q2, amount); }
Quaternion pengu_rm_QuaternionNlerp(Quaternion q1, Quaternion q2, float amount) { return QuaternionNlerp(q1, q2, amount); }
Quaternion pengu_rm_QuaternionSlerp(Quaternion q1, Quaternion q2, float amount) { return QuaternionSlerp(q1, q2, amount); }
Quaternion pengu_rm_QuaternionCubicHermiteSpline(Quaternion q1, Quaternion outTangent1, Quaternion q2, Quaternion inTangent2, float t) { return QuaternionCubicHermiteSpline(q1, outTangent1, q2, inTangent2, t); }
Quaternion pengu_rm_QuaternionFromVector3ToVector3(Vector3 from, Vector3 to) { return QuaternionFromVector3ToVector3(from, to); }
Quaternion pengu_rm_QuaternionFromMatrix(Matrix mat) { return QuaternionFromMatrix(mat); }
Matrix pengu_rm_QuaternionToMatrix(Quaternion q) { return QuaternionToMatrix(q); }
Quaternion pengu_rm_QuaternionFromAxisAngle(Vector3 axis, float angle) { return QuaternionFromAxisAngle(axis, angle); }
void pengu_rm_QuaternionToAxisAngle(Quaternion q, Vector3 *outAxis, float *outAngle) { QuaternionToAxisAngle(q, outAxis, outAngle); }
Quaternion pengu_rm_QuaternionFromEuler(float pitch, float yaw, float roll) { return QuaternionFromEuler(pitch, yaw, roll); }
Vector3 pengu_rm_QuaternionToEuler(Quaternion q) { return QuaternionToEuler(q); }
Quaternion pengu_rm_QuaternionTransform(Quaternion q, Matrix mat) { return QuaternionTransform(q, mat); }
int pengu_rm_QuaternionEquals(Quaternion p, Quaternion q) { return QuaternionEquals(p, q); }
Matrix pengu_rm_MatrixCompose(Vector3 translation, Quaternion rotation, Vector3 scale) { return MatrixCompose(translation, rotation, scale); }
void pengu_rm_MatrixDecompose(Matrix mat, Vector3 *translation, Quaternion *rotation, Vector3 *scale) { MatrixDecompose(mat, translation, rotation, scale); }