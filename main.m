% Super-capacitor voltage vs time with constant power output
clear; clc; close all;

% Define parameters
V1c = 3;            % Initial voltage of cell (V)
Cc = 600;           % Capacitance per cell (F)
P = 8e4;            % Constant power output (W)
tfinish = 4;        % Time to reach minimum voltage (s)
n_caps = 200;       % Number of capacitors
ESR_per_cap = 0.7e-3; % ESR per capacitor (ohms)
ESR_total = ESR_per_cap * n_caps; % Total ESR (ohms)

V1 = V1c*n_caps;    % Total initial voltage (V)
C = Cc/n_caps;      % Total Capacitance (F)

% Calculate inital energy from initial conditions
% E1 = (1/2) * C * V1^2
E1 = 0.5 * C * V1^2;

% Solve ODE with ESR losses
% Energy equation: dE/dt = -P_out - P_ESR = -P - I^2*ESR
% Where E = (1/2)*C*V^2, so dE/dt = C*V*dV/dt
% Current: I = P/V (to maintain constant output power)
% Therefore: C*V*dV/dt = -P - (P/V)^2*ESR
% Simplifying: dV/dt = -P/(C*V) - P^2*ESR/(C*V^3)

% Define ODE function
dVdt = @(t, V) -P./(C*V) - P^2*ESR_total./(C*V.^3);

% Initial condition and time span
tspan = [0, 10]; % Extended time span to ensure we capture full discharge
V0 = V1;

% Solve ODE
options = odeset('Events', @(t,V) eventfcn(t,V), 'RelTol', 1e-6, 'MaxStep', 0.1);
[t_ode, V_ode] = ode45(dVdt, tspan, V0, options);

% Use ODE solution for plotting
t = t_ode;
V = V_ode;

% Recalculate Vmin and tfinish based on ODE solution
% Find Vmin at original tfinish time
idx_tfinish = find(t >= tfinish, 1, 'first');
if ~isempty(idx_tfinish)
    Vmin = V(idx_tfinish);
else
    Vmin = V(end);
end

% Calculate time when voltage drops to near zero
t_end = t(end);

% Calculate current as a function of time
% I = P/V
I = P ./ V;

% Calculate Imax at tfinish
Imax = P / Vmin;

% Create the plot with two y-axes
figure('Position', [100, 100, 800, 600]);
yyaxis left
h1 = plot(t, V, 'b-', 'LineWidth', 2.5);
hold on;
% Draw Vmin line only from 0 to tfinish
h2 = plot([0, tfinish], [Vmin, Vmin], 'r--', 'LineWidth', 1.5);
text(tfinish*0.5, Vmin*1.05, 'V_{min}', 'FontSize', 12, 'Color', 'r');
hold off;
ylabel('Voltage (V)', 'FontSize', 12);
ylim([0, V1*1.1]);

yyaxis right
h3 = plot(t, I, 'Color', [0.7 0.7 0.7], 'LineWidth', 2.5);
hold on;
% Draw Imax line only from tfinish to t_end
h4 = plot([tfinish, t_end], [Imax, Imax], 'k--', 'LineWidth', 1.5);
text((tfinish + t_end)*0.5, Imax*1.1, 'I_{max}', 'FontSize', 12, 'Color', 'k');
% Draw tfinish vertical line
h5 = xline(tfinish, 'm--', 'LineWidth', 1.5);
hold off;
ylabel('Current (A)', 'FontSize', 12);
ylim([0, 1000]);

% Format the plot
xlabel('Time (s)', 'FontSize', 12);
title('Super-Capacitor Voltage and Current vs Time (Constant Power Output)', 'FontSize', 14);
grid on;
legend([h1, h2, h5, h3, h4], {'V(t)', 'V_{min}', 't_{finish}', 'I(t)', 'I_{max}'}, 'Location', 'best');

% Display parameters on the plot
text_str = sprintf('V_1 = %.1f V\nE_1 = %.1f J\nP = %.1f W\nC = %.2f F\nESR = %.2f Ω', ...
                   V1, E1, P, C, ESR_total);
annotation('textbox', [0.15, 0.7, 0.2, 0.15], 'String', text_str, ...
           'FitBoxToText', 'on', 'BackgroundColor', 'white', ...
           'EdgeColor', 'black', 'FontSize', 10);

% Display results
fprintf('Super-Capacitor Analysis:\n');
fprintf('Initial Voltage: %.2f V\n', V1);
fprintf('Initial Energy: %.2f J\n', E1);
fprintf('Capacitance: %.4f F\n', C);
fprintf('Number of Capacitors: %d\n', n_caps);
fprintf('ESR per Capacitor: %.4f ohms\n', ESR_per_cap);
fprintf('Total ESR: %.4f ohms\n', ESR_total);
fprintf('Constant Power: %.2f W\n', P);
fprintf('Finish Time: %.2f s\n', tfinish);
fprintf('Minimum Voltage (at tfinish): %.2f V\n', Vmin);
fprintf('Time to full discharge (V≈0): %.2f s\n', t_end);
fprintf('Average ESR Power Loss: %.2f W\n', mean((P./V).^2 * ESR_total));

% Event function to stop integration when V gets very low
function [value, isterminal, direction] = eventfcn(t, V)
    value = V - 10; % Stop when V drops below 10V
    isterminal = 1; % Stop the integration
    direction = -1; % Detect decreasing values only
end
