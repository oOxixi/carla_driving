# 目标速度、跟车风险与 D 仲裁的交接

上级：[纵向控制模块](../modules/vehicle-longitudinal.md)；关联：[安全模块](../modules/vehicle-safety.md)。

## C 与 D 分别决定什么

C 根据驾驶请求、前车/停止线/灯态与曲率形成 target_speed/target_accel，并控制 throttle/brake；D 接收原始控制、车辆安全状态、命令、风险和 watchdog 告警，决定是否覆盖最终控制。C 提前采取保守制动不意味着 D 已经不再需要。

主要实现：[LongitudinalController](../../../car_control_C/longitudinal_controller.py)、[FollowingController](../../../car_control_C/following_controller.py)、[SafetySupervisor](../../../car_control_D/safety_supervisor.py)、[ControlRuntime](../../../integration/runtime_loop.py)。

## 调整跟车或制动时的具体排查

先看测量 gap/lead speed 是否属于同一对象，再看 desired gap、closing speed、TTC 和 speed cap，最后看 PID/纵向状态及 D reason。距离问题、规划限速问题与执行器饱和不是同一个参数可以修复。

| 维护关注点 | 要一起看的实现/状态 |
|---|---|
| 跟车变保守或过激 | FollowingController 的期望间距/风险/速度上限、传感器接近速度与对象切换 |
| 弯道速度 | route 曲率生成、runtime 的前方 max_abs_curvature_ahead、C 限速参数 |
| 停车后蠕动 | C hold_brake、ControlRuntime._stop_hold、终态后 requested_speed |
| 明明已制动仍报安全覆盖 | D 的 reason_category 和命令终态；安全语义覆盖可能保留同一制动值 |
| 参数改了没有效果 | DrivingPolicy 是否构造覆盖了默认参数、speed_cap 是否更严格、D 是否再次限制 |

量纲为米、米每秒、米每二次方秒及秒；归一化 throttle/brake 不是加速度单位。不能将 C 的目标加速度直接当 CARLA throttle。

## D 封装为何看起来有两套

实时 ControlRuntime 使用 SafetySupervisor；DControlRuntime 提供另一种 canonical 封装并供 benchmark 使用。后续改安全规则要定位共享 Supervisor 与封装各自行为，不根据文件名直接删除“重复”类。测试封装通过不能自动证明实时 runner 用到了相同配置。

验证：[C tests](../../../car_control_C/tests)、[D tests](../../../car_control_D/tests)、[runtime loop tests](../../../integration/tests/test_runtime_loop.py)。需要覆盖低 TTC、目标切换、停车保持、非法控制、过期命令与 watchdog，而不是只测正常巡航。
