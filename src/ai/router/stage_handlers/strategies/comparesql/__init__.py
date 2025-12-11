"""CompareSQL stage strategies."""

from .ask_first_sql_method import AskFirstSQLMethodStrategy
from .need_first_natural_language import NeedFirstNaturalLanguageStrategy
from .need_first_user_sql import NeedFirstUserSQLStrategy
from .confirm_first_sql import ConfirmFirstSQLStrategy
from .ask_second_sql_method import AskSecondSQLMethodStrategy
from .need_second_natural_language import NeedSecondNaturalLanguageStrategy
from .need_second_user_sql import NeedSecondUserSQLStrategy
from .confirm_second_sql import ConfirmSecondSQLStrategy
from .ask_auto_match import AskAutoMatchStrategy
from .waiting_map_table import WaitingMapTableStrategy
from .ask_reporting_type import AskReportingTypeStrategy
from .ask_compare_schema import AskCompareSchemaStrategy
from .ask_compare_table_name import AskCompareTableNameStrategy
from .execute_compare_sql import AskCompareJobNameStrategy, ExecuteCompareSQLStrategy
from .gather_params import GatherCompareParamsStrategy

__all__ = [
    "AskFirstSQLMethodStrategy",
    "NeedFirstNaturalLanguageStrategy",
    "NeedFirstUserSQLStrategy",
    "ConfirmFirstSQLStrategy",
    "AskSecondSQLMethodStrategy",
    "NeedSecondNaturalLanguageStrategy",
    "NeedSecondUserSQLStrategy",
    "ConfirmSecondSQLStrategy",
    "AskAutoMatchStrategy",
    "WaitingMapTableStrategy",
    "AskReportingTypeStrategy",
    "AskCompareSchemaStrategy",
    "AskCompareTableNameStrategy",
    "AskCompareJobNameStrategy",
    "ExecuteCompareSQLStrategy",
    "GatherCompareParamsStrategy",
]
