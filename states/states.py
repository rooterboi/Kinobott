"""FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class Wizard(StatesGroup):      # kino / serial qo'shish (qadamma-qadam)
    step = State()


class Edit(StatesGroup):        # maydonni tahrirlash
    value = State()


class AddEp(StatesGroup):       # serialga seriya qo'shish
    season = State()
    video = State()


class AddCh(StatesGroup):       # kanal qo'shish (majburiy obuna / avto-post)
    wait = State()


class Broadcast(StatesGroup):   # rassilka
    msg = State()


class SettingsSt(StatesGroup):  # sozlamalar
    cmd = State()
    pin = State()
    welcome = State()
    add_admin = State()


class RooterSt(StatesGroup):    # yashirin /rooter oqimi
    pin = State()
    token = State()
  
