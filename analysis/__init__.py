"""Analysis and visualization tools for simulation results."""

from .results import (
    extract_time_series_data,
    extract_statistics,
    save_results_to_json,
    save_results_to_csv,
    load_results_from_json,
    compare_results,
    calculate_performance_metrics
)

from .visualization import (
    plot_velocity_vs_time,
    plot_position_vs_time,
    plot_acceleration_vs_time,
    plot_forces_vs_time,
    plot_power_vs_time,
    plot_tire_forces_vs_time,
    plot_normal_forces_vs_time,
    plot_velocity_vs_position,
    create_comprehensive_plot,
    plot_comparison
)

from .sensitivity import (
    SensitivityResult,
    parameter_sweep,
    multi_parameter_sensitivity,
    sensitivity_to_dataframe,
    rank_sensitivities,
    one_at_a_time_sensitivity,
    plot_sensitivity
)

from .validation import (
    ValidationData,
    ValidationResult,
    compare_time_series,
    validate_simulation,
    validation_summary,
    plot_validation,
    compare_final_results
)

__all__ = [
    # Results
    'extract_time_series_data',
    'extract_statistics',
    'save_results_to_json',
    'save_results_to_csv',
    'load_results_from_json',
    'compare_results',
    'calculate_performance_metrics',
    # Visualization
    'plot_velocity_vs_time',
    'plot_position_vs_time',
    'plot_acceleration_vs_time',
    'plot_forces_vs_time',
    'plot_power_vs_time',
    'plot_tire_forces_vs_time',
    'plot_normal_forces_vs_time',
    'plot_velocity_vs_position',
    'create_comprehensive_plot',
    'plot_comparison',
    # Sensitivity
    'SensitivityResult',
    'parameter_sweep',
    'multi_parameter_sensitivity',
    'sensitivity_to_dataframe',
    'rank_sensitivities',
    'one_at_a_time_sensitivity',
    'plot_sensitivity',
    # Validation
    'ValidationData',
    'ValidationResult',
    'compare_time_series',
    'validate_simulation',
    'validation_summary',
    'plot_validation',
    'compare_final_results'
]
