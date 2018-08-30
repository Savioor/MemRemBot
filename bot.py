# coding=utf-8
import json
import telepot
import time
import datetime
import os.path
import traceback
import hashlib
from random import randint


t0 = datetime.datetime(1970, 1, 1)


class UserError(Exception):
    pass

fni = UserError("Not implemented yet")


def run_rem(bot, user, data, reminder, affect_data=True):
    item = data[reminder]["type"]
    if item == "br":
        return BasicReminder.do_thing(bot, user, data, reminder, affect_data)
    if item == "cr":
        return ContReminder.do_thing(bot, user, data, reminder, affect_data)
    if item == "gr":
        return GroupReminder.do_thing(bot, user, data, reminder, affect_data)


def run_dummy(data, id):
    item = data[id]["type"]
    if item == "br":
        return BasicReminder.dummy_do_thing(data, id)
    if item == "cr":
        return ContReminder.dummy_do_thing(data, id)
    if item == "gr":
        return GroupReminder.dummy_do_thing(data, id)


def run_str(data, id):
    item = data[id]["type"]
    if item == "br":
        return BasicReminder.get_str(data, id)
    if item == "cr":
        return ContReminder.get_str(data, id)
    if item == "gr":
        return GroupReminder.get_str(data, id)


class Reminder(object):

    time_map = {
        "second": 1,
        "minute": 60,
        "hour": 60 * 60,
        "day": 60 * 60 * 24,
        "week": 60 * 60 * 24 * 7,
        "month": 60 * 60 * 24 * 30,
        "year": 60 * 60 * 24 * 365
    }

    def __init__(self):
        self.id = "".join(map(lambda a: chr(ord(a) + 20), str(datetime.datetime.now())))

    def __str__(self):
        return "ID: " + self.id

    @staticmethod
    def get_str(data, id):
        raise fni

    def get_json_compatible(self):
        raise fni

    @staticmethod
    def dummy_do_thing(data, id):
        raise fni

    @staticmethod
    def do_thing(bot, recv, data, id, affect_data=True):
        raise fni

log_number = 1
def log(string):
    global log_number
    print "---------------------------------------------------------------------\n" + \
          "TIME: " + str(datetime.datetime.now()) + "\n" + \
          "LOG NUMBER: " + str(log_number) + "\n\n" \
          "MESSAGE:\n" + str(string)
    log_number += 1


def parse_time(time_str):
    if type(time_str) != list:
        data_splat = filter(lambda a: a != "and", time_str.split(" "))
    else:
        data_splat = time_str
    total_time_secs = 0
    for i in xrange(0, len(data_splat), 2):
        multiplier = float(data_splat[i])
        try:
            total_time_secs += Reminder.time_map[data_splat[i + 1]] * multiplier
        except KeyError:
            try:
                total_time_secs += Reminder.time_map[data_splat[i + 1][:-1]] * multiplier
            except KeyError:
                raise UserError(data_splat[i + 1] + " is not a time unit")
    return total_time_secs


def parse_date(data_str):
    # yyyy/mm/dd hh:mm[:ss]
    # mm/dd hh:mm[:ss]
    # hh:mm[:ss]
    if type(data_str) != list:
        data_splat = data_str.split(" ")
    else:
        data_splat = data_str

    tm_splat = data_splat[-1].split(":")
    hour = int(tm_splat[0])
    minute = int(tm_splat[1])
    if len(tm_splat) == 3:
        second = int(tm_splat[2])
    else:
        second = 0
    if len(data_splat) == 2:
        dt_splat = data_splat[0].split("/")
        month = int(dt_splat[-2])
        day = int(dt_splat[-1])
        if len(dt_splat) == 3:
            year = int(dt_splat[0])
        else:
            t = datetime.datetime.now()
            year = t.year
    else:
        t = datetime.datetime.now()
        year = t.year
        month = t.month
        day = t.day

    return (datetime.datetime(year, month, day, hour, minute, second) - t0).total_seconds()


class GroupReminder(Reminder):

    def __init__(self, group_name, password):
        Reminder.__init__(self)

        if group_name not in groups.keys():
            raise UserError("No group with ID {} exists.".format(group_name))
        if not groups[group_name].auth_join(password):
            raise UserError("Password incorrect.")
        self.group = group_name

    @staticmethod
    def get_str(data, id):
        self = data[id]
        return "ID: " + id + "\n" + \
            "TYPE: group\n" + \
            "GROUP ID: " + self["group"] + "\n" + \
            "GROUP REMINDERS:\n . . . . " + "\n . . . . ".join(str(groups[self["group"]]).split("\n"))

    def get_json_compatible(self):
        return {"group": self.group, "id": self.id, "type": "gr"}

    @staticmethod
    def do_thing(bot, recv, data, id, affect_data=True):
        group = groups[data[id]["group"]]
        group.set_id(recv)
        group.run_all_reminders(bot)
        return data

    @staticmethod
    def dummy_do_thing(data, id):
        return data


class ContReminder(Reminder):

    def __init__(self, date_str):
        # /setcrem every [time] (starting [time]) (that [message])
        Reminder.__init__(self)
        self.trig = False
        self.message = ""
        data_splat = filter(lambda a: a != "and", date_str.split(" "))[1:]

        if "that" in data_splat:
            ind = data_splat.index("that")
            self.message = " ".join(data_splat[ind + 1:])
            data_splat = data_splat[:ind]

        if "starting" in data_splat:
            ind = data_splat.index("starting")
            self.start = parse_date(data_splat[ind + 1:])
            data_splat = data_splat[:ind]
        else:
            self.start = (datetime.datetime.now() - t0).total_seconds()

        self.jump = parse_time(data_splat)

        try:
            int(self.start)
            int(self.jump)
        except:
            raise UserError("You cheeky bastard wtf you doing.")

        if self.jump < 3:
            raise UserError("Total time must be above 3 seconds")
        if self.jump >= Reminder.time_map["year"] * 4:
            raise UserError("Total time must be below 4 years")

    @staticmethod
    def get_str(data, id):
        self = data[id]
        return "ID: " + id + "\n" + \
            "TYPE: continuous reminder\n" + \
            "START TIME: " + str(datetime.datetime.fromtimestamp(self["start"])) + "\n" + \
            "JUMP TIME: " + str(self["jump"]) + " seconds\n" + \
            "MESSAGE: " + self["message"]

    def get_json_compatible(self):
        return {"start": self.start, "jump": self.jump, "message": self.message,
                "id": self.id, "trig": self.trig, "type": "cr"}

    @staticmethod
    def dummy_do_thing(data, id):
        self = data[id]
        if int(((datetime.datetime.now() - t0).total_seconds() - self["start"])) % int(self["jump"]) <= 5:
            if not self["trig"]:
                data[id]["trig"] = True
        else:
            data[id]["trig"] = False
        return data

    @staticmethod
    def do_thing(bot, recv, data, id, affect_data=True):
        self = data[id]
        if int(((datetime.datetime.now() - t0).total_seconds() - self["start"])) % int(self["jump"]) <= 5:
            if not self["trig"]:
                bot.sendMessage(recv, "Reminding you that " + self["message"])
                log("User: " + str(recv) + " recieved a cont reminder with ID: " + id)
                if affect_data:
                    data[id]["trig"] = True
        else:
            if affect_data:
                data[id]["trig"] = False
        return data


class BasicReminder(Reminder):

    def __init__(self, date_str):
        # remind me in n item[s] and ... [that message]
        Reminder.__init__(self)
        self.message = ""
        data_splat = filter(lambda a: a != "and", date_str.split(" "))
        tt = data_splat[0]
        data_splat = data_splat[1:]

        ''' Get The Message '''
        if "that" in data_splat:
            ind = data_splat.index("that")
            self.message = " ".join(data_splat[ind + 1:])
            data_splat = data_splat[:ind]

        ''' Get The Trigger Time '''
        if tt == "in":
            total_time_secs = parse_time(data_splat)
            if total_time_secs < 3:
                raise UserError("Total time must be above 3 seconds")
            if total_time_secs >= Reminder.time_map["year"] * 4:
                raise UserError("Total time must be below 4 years")
            self.trigger_time = (datetime.datetime.now() - t0).total_seconds() + total_time_secs

        elif tt == "at":
            self.trigger_time = parse_date(data_splat)
            delta_time = self.trigger_time - (datetime.datetime.now() - t0).total_seconds()
            if delta_time < 3:
                raise UserError("Total time from now must be above 3 seconds")
            if delta_time >= Reminder.time_map["year"] * 4:
                raise UserError("Total time from now must be below 4 years")

        else:
            raise UserError("'" + tt + "' is not a valid argument for /setbrem")

        ''' Check for cheeky faggots putting NaN as the trigger time '''
        try:
            int(self.trigger_time)
        except:
            raise UserError("You cheeky bastard wtf you doing.")

        if self.message == "":
            self.message = "*** No Message Added ***"

    @staticmethod
    def get_str(data, id):
        self = data[id]
        return "ID: " + id + "\n" + \
            "TYPE: single use reminder\n" + \
            "TRIGGER TIME: " + str(datetime.datetime.fromtimestamp(self["date"])) + "\n" + \
            "MESSAGE: " + self["message"]

    def get_json_compatible(self):
        return {"date": self.trigger_time, "message": self.message, "type": "br", "id": self.id}

    @staticmethod
    def do_thing(bot, recv, data, id, affect_data=True):
        self = data[id]
        if (datetime.datetime.now() - t0).total_seconds() >= self["date"]:
            bot.sendMessage(recv, "Reminding you that " + self["message"])
            if affect_data:
                del data[id]
            log("User: " + str(recv) + " recieved a basic reminder with ID: " + id)
        return data

    @staticmethod
    def dummy_do_thing(data, id):
        self = data[id]
        if (datetime.datetime.now() - t0).total_seconds() >= self["date"]:
            del data[id]
        return data


class Conversation(object):

    def __init__(self, idd):
        self.ID = idd
        self.reminders = str(idd)
        if not os.path.isfile(root + self.reminders + ".json"):
            save_as_json({
                "reminders": {},
                "context": idd
            }, self.reminders)

    def get_str(self):
        toRet = ""
        data = read_json(self.reminders)["reminders"]
        for key in data.keys():
            toRet += run_str(data, key) + "\n~~~~~~~~~~~~~~~~~~~~~~~\n"
        toRet = "\n~~~~~~~~~~~~~~~~~~~~~~~\n".join(toRet.split("\n~~~~~~~~~~~~~~~~~~~~~~~\n")[:-1])
        return toRet

    def run_all_reminders(self, bot):
        data = read_json(self.reminders)

        for key in data["reminders"].keys():
            data["reminders"] = run_rem(bot, self.ID, data["reminders"], key)

        save_as_json(data, self.reminders)

    def remove_reminder(self, ID):
        data = read_json(self.reminders)
        if ID not in data["reminders"]:
            raise UserError("ID {} not valid".format(ID))
        del data["reminders"][ID]
        save_as_json(data, self.reminders)

    def add_basic_reminder(self, date):
        data = read_json(self.reminders)

        if len(data["reminders"]) > 10:
            raise UserError("Oi mate you got a licence for that? (max 10 reminders)")

        toAdd = BasicReminder(date).get_json_compatible()
        data["reminders"][toAdd["id"]] = toAdd

        log("User: " + str(self.reminders) + " added a basic reminder with ID: " + toAdd["id"])
        save_as_json(data, self.reminders)

    def add_group_reminder(self, data_splat):
        data = read_json(self.reminders)

        if len(data["reminders"]) > 10:
            raise UserError("Oi mate you got a licence for that? (max 10 reminders)")

        toAdd = GroupReminder(data_splat[0], data_splat[1]).get_json_compatible()
        data["reminders"][toAdd["id"]] = toAdd

        log("User: " + str(self.reminders) + " added a group reminder with ID: " + toAdd["id"])
        save_as_json(data, self.reminders)

    def add_cont_reminder(self, indata):
        data = read_json(self.reminders)

        if len(data["reminders"]) > 10:
            raise UserError("Oi mate you got a licence for that? (max 10 reminders)")

        toAdd = ContReminder(indata).get_json_compatible()
        data["reminders"][toAdd["id"]] = toAdd

        log("User: " + str(self.reminders) + " added a continuous reminder with ID: " + toAdd["id"])
        save_as_json(data, self.reminders)


class Group(Conversation):

    def __init__(self, idd=None, adminPass=None, joinPass=None):
        self.recipient = None
        self.ID = None
        self.admin_pass = None
        self.join_pass = None
        self.reminders = None
        if idd is None:
            return

        Conversation.__init__(self, idd)

        s = read_json(self.reminders)

        h = hashlib.md5()
        h.update(adminPass)
        self.admin_pass = h.hexdigest()
        h = hashlib.md5()
        h.update(joinPass)
        self.join_pass = h.hexdigest()

        s["admin_pass"] = self.admin_pass
        s["join_pass"] = self.join_pass

        save_as_json(s, self.reminders)

    def run_all_reminders(self, bot):
        data = read_json(self.reminders)

        for key in data["reminders"].keys():
            run_rem(bot, self.ID, data["reminders"], key, False)

    def dummy_run_all(self):
        data = read_json(self.reminders)

        for key in data["reminders"].keys():
            data["reminders"] = run_dummy(data["reminders"], key)

        save_as_json(data, self.reminders)

    @staticmethod
    def create_from_file(idd):
        to_ret = Group()
        to_ret.ID = idd
        to_ret.reminders = str(idd)
        ffile = read_json(to_ret.reminders)
        to_ret.admin_pass = ffile["admin_pass"]
        to_ret.join_pass = ffile["join_pass"]
        return to_ret

    def set_id(self, idd):
        self.ID = idd

    def auth_admin(self, password):
        h = hashlib.md5()
        h.update(password)
        hashed_pass = h.hexdigest()
        return read_json(self.reminders)["admin_pass"] == hashed_pass

    def auth_join(self, password):
        h = hashlib.md5()
        h.update(password)
        hashed_pass = h.hexdigest()
        return read_json(self.reminders)["join_pass"] == hashed_pass

root = "C:/Users/USER/Desktop/RemBot/"


def save_as_json(data, file_name, sort_keys=True, indent=2):
    with open(root + file_name + ".json", "w") as f:
        json.dump(data, f, sort_keys=sort_keys, indent=indent)


def read_json(file_name):
    with open(root + file_name + ".json", "r") as f:
        r = json.load(f)
    return r

users = {}
groups = {}
token = "658973131:AAFrclnxWr764WatQwy_KO3bq6D8-PyRP4c"
illegal = ["\\", "/", ":", "*", "?", "\"", "<", ">", "|"]

if __name__ == "__main__":
    bot = telepot.Bot(token)
    log(bot.getMe())

    active = True

    try:
        last = read_json("bot_data")["next"]
    except KeyError:
        last = 0

    try:
        c = read_json("bot_data")["convos"]
        for p in c:
            users[str(p)] = Conversation(p)
            log("User {} added from database.".format(str(p)))
    except KeyError:
        bd = read_json("bot_data")
        bd["convos"] = []
        save_as_json(bd, "bot_data")

    try:
        c = read_json("bot_data")["groups"]
        for p in c:
            groups[p] = Group.create_from_file(p)
            log("Group {} added from database.".format(str(p)))
    except KeyError:
        bd = read_json("bot_data")
        bd["groups"] = []
        save_as_json(bd, "bot_data")

    log("Bot started up")

    while active:

        msgs = bot.getUpdates(last)
        for msg in msgs:

            log(msg)

            try:
                mfrom = msg["message"]["from"]["id"]
            except KeyError:
                continue

            try:

                msg_splat = msg["message"]["text"].split(" ")

                if str(mfrom) not in users.keys():
                    users[str(mfrom)] = Conversation(mfrom)
                    bd = read_json("bot_data")
                    bd["convos"].append(mfrom)
                    save_as_json(bd, "bot_data")

                if msg_splat[0] == "/setbrem":
                    context = read_json(str(mfrom))["context"]
                    try:
                        users[context].add_basic_reminder(" ".join(msg["message"]["text"].split(" ")[1:]))
                    except KeyError:
                        groups[context].add_basic_reminder(" ".join(msg["message"]["text"].split(" ")[1:]))
                    bot.sendMessage(mfrom, "Reminder successfully set!")

                elif msg_splat[0] == "/setcrem":
                    context = read_json(str(mfrom))["context"]
                    try:
                        users[context].add_cont_reminder(" ".join(msg["message"]["text"].split(" ")[1:]))
                    except KeyError:
                        groups[context].add_cont_reminder(" ".join(msg["message"]["text"].split(" ")[1:]))
                    bot.sendMessage(mfrom, "Reminder successfully set!")

                elif msg_splat[0] == "/help":
                    if len(msg_splat) == 1:
                        bot.sendMessage(mfrom,
                                        "/help - Shows all commands" +
                                        "\n\n/setbrem [in/at] [time/date] that [message] - This will set a reminder at a certain time and date" +
                                        "\n\n/setcrem every [time] starting [date] that [message] - This is a continuous reminder, sending messages every so often" +
                                        "\n\n/editself - Switch to editing your personal reminders" +
                                        "\n\n/startgroup [editing password] [join password] - Create a new group of reminders" +
                                        "\n\n/editgroup [group ID] [edit password] - Start editing the reminders of a group" +
                                        "\n\n/joingroup [group ID] [join password] - Join a group and recieve all of it's reminders" +
                                        "\n\n/showrems - Shows all of your reminders" +
                                        "\n\n/removerem [ID] - Remove a reminder with that ID" +
                                        "\n\ncall '/help [command name]' for more info on that command"
                                        )

                    elif msg_splat[1] == "setbrem":
                        bot.sendMessage(mfrom,
                                        "/setbrem in [time] that [message] -\nThis will remind after the " +
                                        "time period you specified will pass.\n[time] - here you specify the time in this way: " +
                                        "[number] [time unit]. e.g. 5 hours. you can string multiple time units together.\n" +
                                        "[message] - Any string.\n" +
                                        "Example - /setbrem in 1 year 5 months 3 days 100 hours 4 minutes 1 second that this bot is great!\n" +
                                        "NOTE 1: All time units are presented in the example and can be both plural and singular\n" +
                                        "NOTE 2: You can connect the time units using the word \"and\". e.g. 1 hour and 5 minutes.\n\n" +
                                        "/setbrem at [datetime] that [message] - \nThis will remind you at a certain date and time.\n" +
                                        "[message] is the same\n" +
                                        "[datetime] is a date and a time in \"yyyy/mm/dd hh:mm:ss\" or \"hh:mm:ss\"\n" +
                                        "Example - /setbrem at 2020/1/1 0:0 that It's time for 2020 jokes!\n" +
                                        "NOTE 1: Years and seconds are optional. e.g. \"10/35 12:30\"\n" +
                                        "NOTE 2: Time units left out will use their value from the current time"
                                        )

                    elif msg_splat[1] == "setcrem":
                        bot.sendMessage(mfrom,
                                        "/setcrem every [time] starting [date] that [message] -\nThis is a continuous reminder, sending messages every so often\n" +
                                        "[time] - This is a time period specification like in \"/setbrem in\". see setbrem.\n" +
                                        "[date] - This is a date time specification like in \"/setbrem at\". see setbrem.\n" +
                                        "[message] - Some message that will be sent\n" +
                                        "Example - /setcrem every 1 day starting 18:00 that I need to walk the dog\n" +
                                        "NOTE 1: [starting] is optional (using current time when not included)"
                                        )

                    elif msg_splat[1] == "editself":
                        bot.sendMessage(mfrom,
                                        "/editself -\nAfter calling this command all reminders added will be added to the presonal reminder list"
                                        )

                    elif msg_splat[1] == "startgroup":
                        bot.sendMessage(mfrom,
                                        "/startgroup [edit password] [join password] -\n" +
                                        "Create a group for reminders. the edit password will be used when calling " +
                                        "\"/editgroup\" and the join password will be used when calling \"/joingroup\"" +
                                        "\n\nNOTE: The ID of the group will look like this: \"group-CCCCN\" where " +
                                        "C is a charachter and N is a number. When referring to the group only use " +
                                        "\"CCCCN\" without the \"group-\" part"
                                        )

                    elif msg_splat[1] == "joingroup":
                        bot.sendMessage(mfrom,
                                        "/joingroup [group ID] [password] -\n" +
                                        "This command will add a group with a certain ID so you will recieve all " +
                                        "reminders from that group"
                                        )

                    elif msg_splat[1] == "editgroup":
                        bot.sendMessage(mfrom,
                                        "/editgroup [group ID] [password] -\n" +
                                        "After calling this command successfully any reminders added will be added to " +
                                        "the group with the specified ID"
                                        )

                    elif msg_splat[1] == "showrems":
                        bot.sendMessage(mfrom,
                                        "/showrems -\n" +
                                        "Shows all of your reminders.\n" +
                                        "NOTE 1: If you are editing a group the reminders of the group will be shown"
                                        )

                    elif msg_splat[1] == "removerem":
                        bot.sendMessage(mfrom,
                                        "/removerem [ID] -\n" +
                                        "Remove a reminder with that ID.\n" +
                                        "NOTE 1: The ID is as specified by \"/showrems\""
                                        )

                elif msg_splat[0] == "/start":
                    bot.sendMessage(mfrom,
                                    "Hello! I'm a reminder bot. Call /help for more info.\n~~~ Made By Alexey Shapovalov ~~~")

                elif msg_splat[0] == "/showrems":
                    context = read_json(str(mfrom))["context"]
                    try:
                        if context in users:
                            bot.sendMessage(mfrom, users[context].get_str())
                        else:
                            bot.sendMessage(mfrom, groups[context].get_str())
                    except telepot.exception.TelegramError:
                        bot.sendMessage(mfrom, "No reminders")

                elif msg_splat[0] == "/removerem":
                    if len(msg_splat) < 2:
                        raise UserError("Command must be in the following form: \"/removerem [ID]\"")
                    context = read_json(str(mfrom))["context"]
                    try:
                        users[context].remove_reminder(" ".join(msg_splat[1:]))
                    except KeyError:
                        groups[context].remove_reminder(" ".join(msg_splat[1:]))
                    bot.sendMessage(mfrom, "Reminder successfully removed!")

                elif msg_splat[0] == "/closebot":
                    # TODO REMOVE THIS FROM FINAL VERSION
                    active = False

                # GROUP STUFF

                elif msg_splat[0] == "/editself":
                    user_data = read_json(str(mfrom))
                    user_data["context"] = str(mfrom)
                    save_as_json(user_data, str(mfrom))
                    bot.sendMessage(mfrom,
                                    "Now editing personal reminders!")

                elif msg_splat[0] == "/startgroup":
                    if len(msg_splat) != 3:
                        raise UserError("Group creation must be in the form \"/startgroup [edit password] [join password]\"")

                    id_base = "group-"
                    count = 0
                    while count < 4:
                        newchar = chr(randint(33, 126))
                        if newchar not in illegal:
                            count += 1
                            id_base += newchar
                    id_base += "0"
                    id_end = 0
                    while True:
                        if not os.path.isfile(root + id_base + ".json"):
                            break
                        id_end += 1
                        id_base = id_base[:-1] + str(id_end)

                    groups[id_base] = Group(id_base, msg_splat[1], msg_splat[2])
                    s = read_json("bot_data")
                    s["groups"].append(id_base)
                    save_as_json(s, "bot_data")

                    log("Group with ID {} added by {}".format(id_base, str(mfrom)))
                    bot.sendMessage(mfrom, "Group created with ID \"{}\"!".format(id_base))

                elif msg_splat[0] == "/joingroup":
                    if len(msg_splat) != 3:
                        raise UserError("Command must be in the form \"/joingroup [group id] [join password]\"")

                    msg_splat[1] = "group-" + msg_splat[1]

                    context = str(mfrom)

                    users[context].add_group_reminder(msg_splat[1:])

                    bot.sendMessage(mfrom, "Group successfully joined!")

                elif msg_splat[0] == "/editgroup":
                    if len(msg_splat) != 3:
                        raise UserError("Command must be in the form \"/editgroup [group id] [admin password]\"")
                    msg_splat[1] = "group-" + msg_splat[1]
                    if msg_splat[1] not in groups.keys():
                        raise UserError("Group with ID {} does not exist".format(msg_splat[1]))
                    if not groups[msg_splat[1]].auth_admin(msg_splat[2]):
                        raise UserError("Password incorrect")

                    user_data = read_json(str(mfrom))
                    user_data["context"] = msg_splat[1]
                    save_as_json(user_data, str(mfrom))
                    bot.sendMessage(mfrom,
                                    "Now editing \"{}\"!".format(msg_splat[1]))

                else:
                    bot.sendMessage(mfrom,
                                    "\"" + msg_splat[0] + "\" is not a command. Try calling /help")

            except Exception as e:
                if type(e) == UserError:
                    bot.sendMessage(mfrom,
                                    e.message)
                else:
                    bot.sendMessage(mfrom,
                                    "Something happened but I'm not gonna tell you.\n" +
                                    "This might because of a mistake on your side or mine. " +
                                    "If you believe the mistake is on my side please send the time stamp: "
                                    + str(log_number) + " to Alexey.")
                    log("ERROR Encountered: " + e.message + "\nBy: " + str(mfrom))
                    traceback.print_exc()

        if len(msgs) > 0:
            last = msgs[-1]["update_id"] + 1

        bd = read_json("bot_data")
        bd["next"] = last
        save_as_json(bd, "bot_data")

        for key in users.keys():
            users[key].run_all_reminders(bot)
        for key in groups.keys():
            groups[key].dummy_run_all()

        time.sleep(1)

    log("Turned off")
