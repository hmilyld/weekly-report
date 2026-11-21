"""Persistence layer, split by aggregate.

Routers and services use ``from .. import crud`` and call ``crud.<name>``; the
package re-exports every public operation so call sites do not care which module
owns it.
"""

from .app_config import (
    decrypt_api_key,
    encrypt_api_key,
    get_app_config,
    update_app_config,
)
from .reports import (
    delete_daily_report,
    get_daily_report,
    get_daily_report_decrypted,
    get_daily_reports_by_week,
    get_daily_reports_range,
    get_monthly_report,
    get_monthly_reports,
    get_weekly_report,
    get_weekly_reports,
    save_monthly_report,
    save_weekly_report,
    upsert_daily_report,
)
from .tasks import (
    create_task,
    delete_task,
    get_completed_tasks,
    get_completed_tasks_count,
    get_pending_tasks,
    get_task_decrypted,
    get_tasks,
    update_task,
)
from .users import (
    change_password,
    create_user,
    delete_user,
    get_all_users,
    get_user_by_username,
    touch_last_login,
    update_user_role,
)

__all__ = [
    "change_password",
    "create_task",
    "create_user",
    "decrypt_api_key",
    "delete_daily_report",
    "delete_task",
    "delete_user",
    "encrypt_api_key",
    "get_all_users",
    "get_app_config",
    "get_completed_tasks",
    "get_completed_tasks_count",
    "get_daily_report",
    "get_daily_report_decrypted",
    "get_daily_reports_by_week",
    "get_daily_reports_range",
    "get_monthly_report",
    "get_monthly_reports",
    "get_pending_tasks",
    "get_task_decrypted",
    "get_tasks",
    "get_user_by_username",
    "get_weekly_report",
    "get_weekly_reports",
    "save_monthly_report",
    "save_weekly_report",
    "touch_last_login",
    "update_app_config",
    "update_task",
    "update_user_role",
    "upsert_daily_report",
]

# Legacy helpers used by migration tests and migration.py itself.
from .app_config import _get_legacy_api_key_encryption_key  # noqa: F401
