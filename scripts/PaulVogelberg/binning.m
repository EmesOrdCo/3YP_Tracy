% Formula Student Accumulator: Supercapacitor Binning Simulation
clear; clc;

% --- 1. Define Pack Parameters ---
num_purchased = 270;
num_kept = 200;
nominal_C = 600;      % Nominal minimum capacitance (Farads)
max_tolerance = 0.20; % +20% max tolerance
alpha = 3;            % Beta distribution shape parameter
beta_param = 5;       % Beta distribution shape parameter

% --- 2. Generate Simulated Batch ---
% betarnd generates a 0-to-1 array, which we scale by max_tolerance
tolerance_pct = betarnd(alpha, beta_param, num_purchased, 1) * max_tolerance;
raw_capacitances = nominal_C .* (1 + tolerance_pct);

% --- 3. Sort and Select (The "Binning") ---
% Sort descending to group the highest capacitance cells at the top
sorted_cells = sort(raw_capacitances, 'descend');

% Keep the top 200, discard the bottom 70
kept_cells = sorted_cells(1:num_kept);
discarded_cells = sorted_cells(num_kept+1:end);

% --- 4. Calculate Pack Statistics ---
% Series capacitance is the reciprocal of the sum of reciprocals
pack_capacitance = 1 / sum(1 ./ kept_cells);
new_c_min = kept_cells(end);   % The 200th cell (the lowest of the kept batch)
pack_voltage = num_kept * 3.0; % 3.0V max per cell

% --- 5. Display Results in Command Window ---
fprintf('=== ACCUMULATOR BINNING SIMULATION ===\n');
fprintf('Cells Purchased: %d\n', num_purchased);
fprintf('Cells Kept:      %d\n', num_kept);
fprintf('--------------------------------------\n');
fprintf('New Pack C_min:                %.2f Farads\n', new_c_min);
fprintf('True Series Pack Capacitance:  %.4f Farads\n', pack_capacitance);
fprintf('Total Pack Max Voltage:        %d Volts\n', pack_voltage);

% Calculate total energy (E = 1/2 * C * V^2)
total_energy_joules = 0.5 * pack_capacitance * (pack_voltage^2);
fprintf('Total Stored Energy:           %.2f kJ\n', total_energy_joules / 1000);
fprintf('======================================\n');