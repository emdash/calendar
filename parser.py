import ast

tokens = (
    'AT',
    'TIME',
    'AND',
    'COMMA',
    'EACH',
    'DAY',
    'WEEK',
    'EXCEPT',
    'MONTH',
    'THIS',
    'NEXT',
    'LAST',
    'ONCE',
    'TWICE',
    'THRICE',
    'TIMES',
    'REPEATING',
    'OF',
    'TO',
    'FOR',
    'FROM',
    'UNTIL',
    'MONTHNAME',
    'ORDINAL',
    'CARDINAL',
    'WEEKDAY',
    'TODAY',
    'TOMORROW',
    'LPAREN',
    'RPAREN',
    'HOURS',
    'MINUTES',
    )

t_AT = r"@|at"
t_AND = r"and"
t_COMMA = r","
t_EACH = r'every|each'
t_DAY = r'days?'
t_WEEK = r'weeks?'
t_EXCEPT = r"but|except"
t_FOR = r"for"
t_HOURS = r"hours?"
t_MINUTES = r"minutes?"

import re

timeregex = re.compile(r"(\d\d?)(:\d\d)?(am|pm)?")
def t_TIME(t):
    r"(\d\d?)(:\d\d)?(am|pm)"
    h, m, phase = timeregex.match(t.value).groups()
    h = int(h)
    m = int(m[1:]) if m else 0
    if phase == "pm" and h < 12:
        h += 12
    t.value = datetime.time(hour = h, minute = m) 
    return t

def t_WEEKDAY(t):
    (
        r"monday"
        r"|tuesday"
        r"|wednesday"
        r"|thursday"
        r"|friday"
        r"|saturday"
        r"|sun"
        r"|mon"
        r"|tue"
        r"|wed"
        r"|thu"
        r"|fri"
        r"|sat"
        r"|sun"
        )
    t.value = day_name_to_num(t.value)
    return t

def t_MONTHNAME(t):
    (
        r"january"
        r"|february"
        r"|march"
        r"|april"
        r"|may"
        r"|june"
        r"|july"
        r"|august"
        r"|september"
        r"|october"
        r"|november"
        r"|december"
        r"|jan"
        r"|feb"
        r"|mar"
        r"|apr"
        r"|may"
        r"|jun"
        r"|jul"
        r"|aug"
        r"|sep"
        r"|sept"
        r"|oct"
        r"|nov"
        r"|dec"
        )
    t.value = month_name_to_num(t.value)
    return t

import string

def t_ORDINAL(t):
    r"\d*(1st|2nd|3rd|\dth)"
    t.value = int("".join((c for c in t.value if c in string.digits)))
    return t

def t_CARDINAL(t):
    r"\d+"
    t.value = int(t.value)
    return t

t_MONTH = r"month"

def t_THIS(t):
    r"this"
    return t

t_NEXT = r"next"
t_LAST = r"last"
t_OF = r"of"
t_TO = r"to"
t_FROM = r"starting|from"
t_TIMES = r"times?"
t_ONCE = r"once"
t_TWICE = r"twice"
t_THRICE = r"thrice"
t_REPEATING = r"repeating?"
t_UNTIL = r"ending|until|til"
t_TODAY = r"now|today"
t_TOMORROW = r"tomorrow"
t_LPAREN = r'\('
t_RPAREN = r'\)'

t_ignore = " \t"

def t_error(t):
    print ("Illegal character '%s'" % t.value[0])

import ply.lex as lex
lex.lex()

import datetime

def day_name_to_num(name):
    
    days = {
        "mon" : 0,
        "tue" : 1,
        "wed" : 2,
        "thu" : 3,
        "fri" : 4,
        "sat" : 5,
        "sun" : 6,
        }

    return days[name[:3]]

def make_date(year=None, month=None, day=None):
    today = datetime.date.today()
    return datetime.date(
        year if year else today.year,
        month if month else today.month,
        day if day else today.day)

def days_from_now(weekday):
    return (weekday - datetime.date.today().weekday()) % 7

def from_day_of_week(weekday, relative='this'):
    offsets = {
        'last' : -7,
        'this' : 0,
        'next' : 7
        }

    return datetime.date.fromordinal(
        datetime.date.today().toordinal() + days_from_now(weekday) +
        offsets[relative])

def month_name_to_num(name):
    months = {
        "jan" : 1,
        "feb" : 2,
        "mar" : 3,
        "apr" : 4,
        "may" : 5,
        "jun" : 6,
        "jul" : 7,
        "aug" : 8,
        "sep" : 9,
        "oct" : 10,
        "nov" : 11,
        "dec" : 12,
        }
    return months[name[:3]]

## misc

def p_and_(t):
    '''and : AND
           | COMMA'''
    t[0] = t[1]

def p_until(t):
    '''until : UNTIL
             | TO'''
    t[0] = t[1]

## numbers

def p_number(t):
    '''number : ORDINAL
              | CARDINAL'''
    t[0] = t[1]

## counts

def p_count_n_times(t):
    '''count : CARDINAL TIMES'''
    t[0] = t[1]

def p_count_once(t):
    '''count : ONCE'''
    t[0] = 2

def p_count_twice(t):
    '''count : TWICE'''
    t[0] = 3

def p_count_thrice(t):
    '''count : THRICE'''
    t[0] = 4

## durations

def p_duration_hours(t):
    '''duration : CARDINAL HOURS'''
    t[0] = datetime.timedelta(hours=t[1])
    
def p_duration_hours_minutes(t):
    '''duration : CARDINAL HOURS CARDINAL MINUTES'''
    t[0] = datetime.timedelta(hours=t[1], minutes=t[3])
    
def p_duration_hours_and_minutes(t):
    '''duration : CARDINAL HOURS and CARDINAL MINUTES'''
    t[0] = datetime.timedelta(hours=t[1], minutes=t[4])

def p_duration_minutes(t):
    '''duration : CARDINAL MINUTES'''
    t[0] = datetime.timedelta(minutes=t[1])
    
## weekdays

def p_weekday_unqualified(t):
    '''weekday : WEEKDAY'''
    t[0] = (t[1], 'this')
    
def p_weekday_qualified(t):
    '''weekday : THIS WEEKDAY
               | LAST WEEKDAY
               | NEXT WEEKDAY
    '''
    t[0] = (t[2], t[1])

def p_weekdays_recursive(t):
    '''weekdays : WEEKDAY and weekdays'''
    t[0] = (t[1],) + t[3]

def p_weekdays_terminal(t):
    '''weekdays : WEEKDAY'''
    t[0] = (t[1],)

## date productions

def p_date_today(t):
    'date : TODAY'
    t[0] = datetime.date.today()

def p_date_tomorrow(t):
    'date : TOMORROW'
    t[0] = datetime.date.today() + datetime.timedelta(days=1)

def p_date_weekday(t):
    'date : weekday'
    t[0] = from_day_of_week(*t[1])

def p_date_month(t):
    'date : MONTHNAME'
    t[0] = make_date(month=t[1],
                     day=1)

def p_date_ordinal(t):
    'date : ORDINAL'
    t[0] = make_date(day=t[1])

def p_date_month_day(t):
    '''date : MONTHNAME number'''
    month, day = t[1], t[2]
    t[0] = make_date(month=month, day=day)

def p_date_day_month(t):
    '''date : number OF MONTHNAME'''
    month, day = t[3], t[1]
    t[0] = make_date(month=month, day=day)

def p_dates_recursive(t):
    '''dates : date and dates'''
    t[0] = (t[1],) + t[3]

def p_dates_terminal(t):
    '''dates : date'''
    t[0] = (t[1],)

## datetimeset productions

def p_datetimeset_dates(t):
    '''datetimeset : dates'''
    t[0] = ast.DateSet(*t[1])

def p_datetimeset_every_day(t):
    '''datetimeset : EACH DAY'''
    t[0] = ast.Daily(datetime.date.today(), 1)

def p_datetimeset_every_day_from(t):
    '''datetimeset : EACH DAY FROM date'''
    t[0] = ast.Daily(t[4], 1)

def p_datetimeset_daily(t):
    '''datetimeset : EACH CARDINAL DAY'''
    t[0] = ast.Daily(datetime.date.today(), t[2])

def p_datetimeset_daily_from(t):
    '''datetimeset : EACH CARDINAL DAY FROM date'''
    t[0] = ast.Daily(t[5], t[2])

def p_datetimeset_weekly(t):
    '''datetimeset : EACH weekdays'''
    t[0] = ast.Weekly(*t[2])

def p_datetimeset_nth_weekday(t):
    '''datetimeset : EACH ORDINAL weekdays'''
    t[0] = ast.NthWeekday(t[2], None, *t[3])

def p_datetimeset_nth_weekday_of(t):
    '''datetimeset : EACH ORDINAL weekdays OF MONTHNAME'''
    t[0] = ast.NthWeekday(t[2], t[5], *t[3])

def p_datetimeset_last_weekday_of(t):
    '''datetimeset : EACH LAST weekdays OF MONTHNAME'''
    t[0] = ast.NthWeekday(-1, t[5], *t[3])
    
def p_datetimeset_last_weekday(t):
    '''datetimeset : EACH LAST weekdays'''
    t[0] = ast.NthWeekday(-1, None, *t[3])

def p_datetimeset_nth_to_last_wekday(t):
    '''datetimeset : EACH ORDINAL TO LAST weekdays'''
    t[0] = ast.NthWeekday(-t[2], None, *t[5])

def p_datetimeset_nth_to_last_weekday_of(t):
    '''datetimeset : EACH ORDINAL TO LAST weekdays OF MONTHNAME'''
    t[0] = ast.NthWeekday(-t[2], t[7], *t[5])

def p_datetimeset_ordinal_of_month(t):
    '''datetimeset : number OF EACH MONTH'''
    t[0] = ast.Monthly(None, t[1])

def p_datetimeset_ordinal_of_monthname(t):
    '''datetimeset : number OF EACH MONTHNAME'''
    t[0] = ast.Monthly(t[4], t[1])

def p_datetimeset_month_ordinal(t):
    '''datetimeset : EACH MONTHNAME number'''
    t[0] = ast.Monthly(t[2], t[3])

def p_datetimeset_except(t):
    '''datetimeset : datetimeset EXCEPT datetimeset'''
    t[0] = ast.Except(t[1], t[3])

def p_datetimeset_and_datetimeset(t):
    '''datetimeset : datetimeset and datetimeset'''
    t[0] = ast.And(t[1], t[3])

def p_datetimeset_from(t):
    '''datetimeset : datetimeset FROM date'''
    t[0] = ast.From(t[1], t[3])

def p_datetimeset_until(t):
    '''datetimeset : datetimeset until date'''
    t[0] = ast.Until(t[1], t[3])

def p_datetimeset_for_days(t):
    '''datetimeset : datetimeset FOR CARDINAL DAY'''
    t[0] = ast.Until(t[1], datetime.date.today() +
                     datetime.timedelta(days=t[3]))

def p_datetimeset_for_weeks(t):
    '''datetimeset : datetimeset FOR CARDINAL WEEK'''
    t[0] = ast.Until(t[1], datetime.date.today() +
                     datetime.timedelta(days=t[3] * 7))

def p_datetimeset_repeating(t):
    '''datetimeset : datetimeset REPEATING count'''
    t[0] = ast.For(t[1], t[3])

def p_datetimeset_group(t):
    '''datetimeset : LPAREN datetimeset RPAREN'''
    t[0] = t[2]

def p_datetimeset_at_time_for_duration(t):
    '''datetimeset : datetimeset AT TIME FOR duration'''
    t[0] = ast.Period(t[1], t[3], t[5])

def p_datetimeset_from_start_to_end(t):
    '''datetimeset : datetimeset FROM TIME until TIME
                   | datetimeset AT TIME until TIME'''
    t[0] = ast.Period(t[1], t[3], t[5])

def p_error(t):
    print("Syntax error at '%s'" % t.value)

start = 'datetimeset'

import ply.yacc as yacc
yacc.yacc()
    
while 1:
    try:
        s = raw_input('dates > ').lower()
    except EOFError:
        break
    print yacc.parse(s)
