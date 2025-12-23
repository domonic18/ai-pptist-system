"""
通用工具模块包
提供项目通用的工具函数和辅助类
"""

from .config_utils import (
    get_project_root,
    load_env_file,
    get_workspace_path,
    get_backend_path,
    get_config_path,
    parse_list_config,
    parse_json_config,
    ensure_directory_exists
)

from .id_utils import (
    generate_uuid,
    generate_short_id,
    generate_numeric_id,
    is_valid_uuid,
    generate_id_with_prefix,
    generate_image_id,
    generate_presentation_id,
    generate_user_id,
    generate_session_id
)

from .datetime_utils import (
    get_current_timestamp,
    get_current_timestamp_ms,
    format_datetime,
    parse_datetime,
    get_today_start,
    get_today_end,
    get_week_start,
    get_week_end,
    get_month_start,
    get_month_end,
    is_within_time_range,
    format_duration,
    get_time_diff,
    is_expired
)

from .string_utils import (
    truncate_string,
    remove_extra_spaces,
    is_valid_email,
    is_valid_url,
    camel_to_snake,
    snake_to_camel,
    extract_numbers,
    extract_emails,
    extract_urls,
    count_words,
    is_contains_chinese,
    is_contains_english,
    normalize_filename,
    generate_slug,
    mask_sensitive_info
)

from .file_utils import (
    get_file_size,
    get_file_extension,
    is_valid_image_extension,
    calculate_file_hash,
    ensure_directory_exists,
    safe_delete_file,
    get_mime_type,
    get_human_readable_size,
    is_file_locked,
    find_files_by_pattern,
    get_file_creation_time,
    get_file_modification_time,
    copy_file_with_metadata,
    get_relative_path
)

from .validation_utils import (
    is_valid_integer,
    is_valid_float,
    is_valid_boolean,
    is_valid_list,
    is_valid_dict,
    is_valid_hex_color,
    is_valid_rgb_color,
    is_valid_percentage,
    is_valid_coordinate,
    is_valid_dimension,
    is_valid_file_size,
    is_valid_image_dimensions,
    is_valid_enum_value,
    is_valid_range,
    is_valid_ratio,
    validate_and_convert_bool,
    validate_and_convert_int,
    validate_and_convert_float
)

from .json_utils import (
    ResponseParser
)

from .async_utils import (
    run_async,
    async_context,
    AsyncRunner
)

__all__ = [
    # config_utils
    'get_project_root', 'load_env_file', 'get_workspace_path', 'get_backend_path',
    'get_config_path', 'parse_list_config', 'parse_json_config', 'ensure_directory_exists',

    # id_utils
    'generate_uuid', 'generate_short_id', 'generate_numeric_id', 'is_valid_uuid',
    'generate_id_with_prefix', 'generate_image_id', 'generate_presentation_id',
    'generate_user_id', 'generate_session_id',

    # datetime_utils
    'get_current_timestamp', 'get_current_timestamp_ms', 'format_datetime', 'parse_datetime',
    'get_today_start', 'get_today_end', 'get_week_start', 'get_week_end',
    'get_month_start', 'get_month_end', 'is_within_time_range', 'format_duration',
    'get_time_diff', 'is_expired',

    # string_utils
    'truncate_string', 'remove_extra_spaces', 'is_valid_email', 'is_valid_url',
    'camel_to_snake', 'snake_to_camel', 'extract_numbers', 'extract_emails',
    'extract_urls', 'count_words', 'is_contains_chinese', 'is_contains_english',
    'normalize_filename', 'generate_slug', 'mask_sensitive_info',

    # file_utils
    'get_file_size', 'get_file_extension', 'is_valid_image_extension', 'calculate_file_hash',
    'ensure_directory_exists', 'safe_delete_file', 'get_mime_type', 'get_human_readable_size',
    'is_file_locked', 'find_files_by_pattern', 'get_file_creation_time',
    'get_file_modification_time', 'copy_file_with_metadata', 'get_relative_path',

    # validation_utils
    'is_valid_integer', 'is_valid_float', 'is_valid_boolean', 'is_valid_list',
    'is_valid_dict', 'is_valid_hex_color', 'is_valid_rgb_color', 'is_valid_percentage',
    'is_valid_coordinate', 'is_valid_dimension', 'is_valid_file_size',
    'is_valid_image_dimensions', 'is_valid_enum_value', 'is_valid_range',
    'is_valid_ratio', 'validate_and_convert_bool', 'validate_and_convert_int',
    'validate_and_convert_float',

    # json_utils
    'ResponseParser',

    # async_utils
    'run_async', 'async_context', 'AsyncRunner'
]