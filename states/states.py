from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    gender = State()
    name = State()
    age = State()
    bio = State()
    photo = State()
    city = State()


class Browse(StatesGroup):
    browsing = State()


class Payment(StatesGroup):
    waiting_payment = State()
