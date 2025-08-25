from enum import Enum

class Lesson(Enum):
    Private_Month = 'Private-Month', 'Private', 1, 1, [129, 150, 160, 180, 220]
    Private_Month_Twice = 'Private-Month_Twice_week', 'Private', 1, 2, [110]
    Private_Three_Months = 'Private_3_Months', 'Private', 3, 1, [504, 540]
    Private_Six_Months = 'Private_6_Months', 'Private', 6, 1, [1080, 840, 960]
    Private_Six_Months_Twice = 'Private_6_Months_Twice_week', 'Private', 6, 2, [2180]
    Private_Year = 'Private_Year', 'Private', 12, 1, [1920]


    Group_Month = 'Group-Month', 'Group', 1, 1, [60, 80, 160, 240, 129, 120, 149]
    Group_Month_Twice = 'Group-Month_Twice_week', 'Group',1, 2, [99]
    Group_Six_Months = 'Group_6_Months', 'Group', 6, 1, [420, 225]
    Group_Six_Months_Twice = 'Group_6_Months_Twice_week', 'Group', 6, 2, [534]


    def __init__(self, label: str, class_type: str, months: int, times: int, cost_options: list):
        self.label = label
        self.class_type = class_type
        self.months = months
        self.times = times
        self.cost_options = cost_options

    def include(self, x:int):
        return x in self.cost_options



    @classmethod
    def from_label(cls, label):
        for item in cls:
            if item.label == label:
                return item


def find_class_type(x):
    lesson_types = [
        Lesson.Private_Month,
        Lesson.Private_Month_Twice,
        Lesson.Private_Three_Months,
        Lesson.Private_Six_Months,
        Lesson.Private_Six_Months_Twice,
        Lesson.Private_Year,

        Lesson.Group_Month,
        Lesson.Group_Month_Twice,
        Lesson.Group_Six_Months,
        Lesson.Group_Six_Months_Twice
    ]
    for lesson in lesson_types:
        if lesson.include(x):
            return lesson
    print(f"missing amount {x}")
