# FSM состояния для экспорта
from aiogram.fsm.state import StatesGroup, State

class ExportState(StatesGroup):
    choosing_period_type = State()  # весь период / конкретный месяц
    choosing_month = State()
    choosing_year = State()

class AnalyticsState(StatesGroup):
    choosing_year = State()
    choosing_start_date = State()
    choosing_end_date = State()

