# This is a patch to apply to solver.py
# Replace lines 172-179 with update_storage=False

# OLD:
#         wheel_torque, motor_current, power = self.powertrain.calculate_torque(
#             requested_torque,
#             motor_speed,
#             state.velocity,
#             dt=self.dt
#         )

# NEW:
#         wheel_torque, motor_current, power = self.powertrain.calculate_torque(
#             requested_torque,
#             motor_speed,
#             state.velocity,
#             dt=self.dt,
#             update_storage=False  # Don't update during RK4 intermediate steps
#         )
