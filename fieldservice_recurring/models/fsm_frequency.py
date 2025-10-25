# Copyright (C) 2019 Brian McMaster, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import pytz
from dateutil.rrule import (
    DAILY,
    FR,
    MO,
    MONTHLY,
    SA,
    SU,
    TH,
    TU,
    WE,
    WEEKLY,
    YEARLY,
    rrule,
)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
import calendar
from datetime import timedelta

WEEKDAYS = {"mo": MO, "tu": TU, "we": WE, "th": TH, "fr": FR, "sa": SA, "su": SU}

FREQUENCIES = {"yearly": YEARLY, "monthly": MONTHLY, "weekly": WEEKLY, "daily": DAILY}

FREQUENCY_SELECT = [
    ("yearly", "Yearly"),
    ("monthly", "Monthly"),
    ("weekly", "Weekly"),
    ("daily", "Daily"),
]


class FSMFrequency(models.Model):
    _name = "fsm.frequency"
    _description = "Frequency Rule for Field Service Orders"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    interval = fields.Integer(
        string="Repeat Every",
        help="The number of intervals between events",
        default=1,
        required=True,
        tracking=True,
    )
    interval_type = fields.Selection(
        FREQUENCY_SELECT,
        required=True,
        tracking=True,
    )
    is_exclusive = fields.Boolean(
        string="Exclusive Rule?",
        help="""Checking this box will make this an exclusive rule. Exclusive
            rules prevent the configured days from being a schedule option""",
    )
    company_id = fields.Many2one("res.company", "Company")
    use_bymonthday = fields.Boolean(
        string="Use Day of Month",
        help="""When selected you will be able to specify which calendar day
            of the month the event occurs on""",
    )
    month_day = fields.Integer(string="Day of Month", tracking=True)

    use_byweekday = fields.Boolean(
        string="Use Days of Week",
        help="""When selected you will be able to choose which days of the
            week the scheduler will include (or exclude if Exclusive rule)""",
    )
    mo = fields.Boolean("Monday")
    tu = fields.Boolean("Tuesday")
    we = fields.Boolean("Wednesday")
    th = fields.Boolean("Thursday")
    fr = fields.Boolean("Friday")
    sa = fields.Boolean("Saturday")
    su = fields.Boolean("Sunday")

    use_bymonth = fields.Boolean(string="Use Months")
    jan = fields.Boolean("January")
    feb = fields.Boolean("February")
    mar = fields.Boolean("March")
    apr = fields.Boolean("April")
    may = fields.Boolean()
    jun = fields.Boolean("June")
    jul = fields.Boolean("July")
    aug = fields.Boolean("August")
    sep = fields.Boolean("September")
    oct = fields.Boolean("October")
    nov = fields.Boolean("November")
    dec = fields.Boolean("December")

    use_by_week = fields.Boolean(string="Use Weeks")
    week_1 = fields.Boolean(string="Week 1")
    week_2 = fields.Boolean(string="Week 2")
    week_3 = fields.Boolean(string="Week 3")
    week_4 = fields.Boolean(string="Week 4")

    use_setpos = fields.Boolean(string="Use Position")
    set_pos = fields.Integer(
        string="By Position",
        help="""Specify an occurrence number, positive or negative,
            corresponding to the nth occurrence of the rule inside
            the frequency period. For example, -1 if combined with a
            'Monthly' frequency, and a weekday of (MO, TU, WE, TH, FR),
            will result in the last work day of every month.""",
    )

    @api.constrains("set_pos")
    def _check_set_pos(self):
        for rec in self:
            if rec.use_setpos:
                if not (-366 < rec.set_pos < 366):
                    raise UserError(_("Position must be between -366 and 366"))

    @api.constrains("month_day")
    def _check_month_day(self):
        for rec in self:
            if rec.use_bymonthday:
                if not (1 <= rec.month_day <= 31):
                    raise UserError(_("'Day of Month must be between 1 and 31"))

    def _get_week_of_month(self, date_obj):
        first_day = date_obj.replace(day=1)
        dom = date_obj.day
        adjusted_dom = dom + first_day.weekday()
        if int(adjusted_dom / 7) + 1 > 4:
            return  4
        return int(adjusted_dom / 7) + 1
        # FIRST WAY
        # month_calendar = calendar.monthcalendar(date_obj.year, date_obj.month)
        # for week_index, week in enumerate(month_calendar, start=1):
        #     if date_obj.day in week:
        #         return week_index

        # SECOND WAY
        # month_weeks = calendar.monthcalendar(date_obj.year, date_obj.month)
        # week_num = 0
        # for week in month_weeks:
        #     if max(week) == 0:
        #         continue  # skip completely empty weeks (shouldn’t happen)
        #     if any(day > 0 for day in week):  # valid week with actual days
        #         week_num += 1
        #     if date_obj.day in week:
        #         return week_num


    def _allowed_week_numbers(self):
        weeks = []
        if self.use_by_week:
            if self.week_1:
                weeks.append(1)
            if self.week_2:
                weeks.append(2)
            if self.week_3:
                weeks.append(3)
            if self.week_4:
                weeks.append(4)
        return weeks

    def _get_relative_week_number(self, start_date, current_date):
        """
        Calculate week number from start_date in 7-day blocks.
        Week 1 = start_date to start_date + 6 days
        """
        delta_days = (current_date.date() - start_date.date()).days
        if delta_days < 0:
            return None  # date is before start_date
        if (delta_days // 7) + 1 > 4:
            return 4
        return (delta_days // 7) + 1

    def _get_rrule(self, dtstart=None, until=None, tz=None):
        self.ensure_one()
        freq = FREQUENCIES[self.interval_type]
        # localize dtstart and until to user timezone
        tz = pytz.timezone(
            tz or self._context.get("tz", None) or self.env.user.tz or "UTC"
        )

        if dtstart:
            dtstart = pytz.timezone("UTC").localize(dtstart).astimezone(tz)
        if until:
            until = pytz.timezone("UTC").localize(until).astimezone(tz)
            # We force until in the starting timezone to avoid incoherent results
            until = tz.normalize(until.replace(tzinfo=dtstart.tzinfo))

        allowed_weeks = self._allowed_week_numbers()
        return (
            # Replace original timezone with current date timezone
            # without changing the time and force it back to UTC,
            # this will keep the same final time even in case of
            # daylight saving time change
            #
            # for instance recurring weekly
            # from 2022-03-21 15:00:00+01:00 to 2022-04-11 15:30:00+02:00
            # will give:
            #
            # utc naive -> datetime timezone aware
            # 2022-03-21 14:00:00 -> 2022-03-21 15:00:00+01:00
            # 2022-03-28 13:00:00 -> 2022-03-28 15:00:00+02:00
            date.replace(tzinfo=tz.normalize(date).tzinfo)
            .astimezone(pytz.UTC)
            .replace(tzinfo=None)
            for date in rrule(
                freq,
                interval=self.interval,
                dtstart=dtstart,
                until=until,
                byweekday=self._byweekday(),
                bymonth=self._bymonth(),
                bymonthday=self._bymonthday(),
                bysetpos=self._bysetpos(),
            )
            if not allowed_weeks or self._get_relative_week_number(dtstart, date) in allowed_weeks
            # if not allowed_weeks or self._get_week_of_month(date.date()) in allowed_weeks
        )

    def _byweekday(self):
        """
        Checks day of week booleans and builds the value for rrule parameter
        @returns: {list} byweekday: list of WEEKDAY values used for rrule
        """
        self.ensure_one()
        if not self.use_byweekday:
            return None
        weekdays = ["mo", "tu", "we", "th", "fr", "sa", "su"]
        byweekday = [WEEKDAYS[field] for field in weekdays if self[field]]
        return byweekday

    def _bymonth(self):
        """
        Checks month booleans and builds the value for rrule parameter
        @returns: {list} bymonth: list of integers used for rrule
        """
        self.ensure_one()
        if not self.use_bymonth:
            return None
        months = [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ]
        return [months.index(field) + 1 for field in months if self[field]]

    def _bymonthday(self):
        self.ensure_one()
        if not self.use_bymonthday:
            return None
        return self.month_day

    def _bysetpos(self):
        self.ensure_one()
        if not self.use_setpos or self.set_pos == 0:
            return None
        return self.set_pos
