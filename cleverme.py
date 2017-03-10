from cleverwrap import CleverWrap
from slackclient import SlackClient
import clever
import time
from random import random
from bisect import bisect
from config import *
import redis
import sys

print(str(time.time()) + ': Initializing CleverMe...')
sc = SlackClient(slack_token)
client = [CleverWrap(official_cleverbot_key), clever.CleverBot(user=cleverio_user, key=cleverio_key, nick=cleverio_nick)]
storage = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)
print(str(time.time()) + ': finished initializing.')


def slack_config(sc, slack_bot_id='', slack_bot_user=''):
    # getting channel ID
    channels = sc.api_call('channels.list')['channels']
    verbosity(channels, True)
    slack_channel_id = ''
    for channel in channels:
        if channel['name'] in slack_channel_name:
            slack_channel_id = channel['id']
            break
    del channels

    if len(slack_welcome_msg) > 0:
        slack_message(slack_welcome_msg)

    # getting bot id
    if len(slack_bot_id) is 0 or len(slack_bot_user) is 0:
        result = sc.api_call('channels.history', channel=slack_channel_id)
        verbosity(result, True)
        for msg in result['messages']:
            try:
                if 'B' in msg['bot_id']:
                    slack_bot_id = msg['bot_id']
                    slack_bot_user = msg['user']
                    break
            except:
                pass
        del result
    return slack_bot_id, slack_bot_user, slack_channel_id


def weighted_choice(choices):
    # https://stackoverflow.com/questions/3679694/a-weighted-version-of-random-choice/3679747#3679747
    values, weights = zip(*choices)
    total = 0
    cum_weights = []
    for w in weights:
        total += w
        cum_weights.append(total)
    x = random() * total
    i = bisect(cum_weights, x)
    return values[i]


def save(storage):
    try:
        cs, convo_id = client[0].save()
        storage.set('cs', cs)
        storage.set('convo_id', convo_id)
        return True
    except:
        verbosity("Error saving conversation information.", True)
        return False


def load(storage):
    try:
        cs = storage.get('cs')
        convo_id = storage.get('convo_id')
        client[0].load(cs=cs, convo_id=convo_id)
        return True
    except:
        verbosity("Error loading previous conversation.", True)
        return False


def newest_message(sc, slack_bot_id, slack_bot_user, slack_channel_id, last_ts=0):
    msg_final = ''
    ts = last_ts
    while ts == last_ts:
        try:
            message = sc.api_call('channels.history', channel=slack_channel_id, count=1)
            verbosity(message, True)
            for msg in message['messages']:
                skip = False
                try:
                    if 'bot_message' in msg['subtype']:
                        verbosity('.newest_message(): message from bot? True; skip? True', True)
                        skip = True
                except:
                    pass
                try:
                    if slack_bot_id in msg['bot_id'] or slack_bot_user in msg['user']:
                        verbosity('.neweest_message(): is bot message? True; skip? True', True)
                        skip = True
                except:
                    pass
                try:
                    if msg['subtype'] == 'file_share' and not skip:
                        verbosity('.newest_message(): is file? True; skip? False break? True', True)
                        msg_final = msg['file']['title']
                        ts = msg['ts']
                        break
                except:
                    pass

                if not skip:
                    verbosity('.newest_message(): is normal message? True', True)
                    msg_final = msg['text']
                    ts = msg['ts']
                    break
        except:
            verbosity('Unable to get newest message from slack!', True, True)
            pass
        time.sleep(1)

    return msg_final, ts


def cb_ask(msg, wdym_sent):
    verbosity('Asking: ' + msg)
    try:
        id = 0
        result = 'I have not an answer for you...'
        error = False
        msg_wdym = 'You will have to explain things to me when I do not reply.'
        if id is 0:
            try:
                result = client[0].say(msg)
            except:
                verbosity('Unable to contact Cerverbot.com API!', True, True)
                try:
                    result = client[1].query(msg)
                    id = 1
                except:
                    verbosity('Unable to contact Cleverbot.io API!!', True, True)

        if id is 1:
            if result == '' or result == ' ':
                result = '*silent*'
                error = False
            else:
                try:
                    if result['status'] == 'Error, the reference "" does not exist':
                        error = True
                        if not wdym_sent:
                            result = msg_wdym
                            wdym_sent = True
                            error = False
                except:
                    error = False
        else:
            error = False

        return error, wdym_sent, result
    except:
        verbosity('-error-: Having trouble thinking for myself!', True, True)
        return False, wdym_sent, "I'm having trouble thinking for myself."


def nap_time(energy, last_restore):
    energy -= 1
    if last_restore <= (time.time()-(60*60)):
        last_restore = time.time()
        energy = 100
        verbosity('.nap_time(): resetting energy', True)
    elif energy == 0:
        slack_message("brb")
        sleep_for = weighted_choice([(60, 25), (30, 50), (25, 25), (15, 5)])
        time.sleep(sleep_for)
        verbosity('.nap_time(): sleeping for ' + str(sleep_for), True)
        slack_message("back")
        last_restore = time.time()
        energy = 100

    time.sleep(3)
    return energy, last_restore


def slack_message(message):
    verbosity('Reply: ' + str(''.join(message)))
    slack_message_result = sc.api_call("chat.postMessage", channel=slack_channel_name, text=str(''.join(message)), as_user=True)
    verbosity(slack_message_result, True)


def verbosity(msg, debug=False, error=False):
    if (debug_verbose and debug) or error or (convo_verbose and not debug):
        print(str(time.time()) + ': ' + str(msg))

verbosity('Loading configuration...')
slack_bot_id, slack_bot_user, slack_channel_id = slack_config(sc, slack_bot_id, slack_bot_user)
last_ts = 0
wdym_sent = False
error = False
energy = 100
last_restore = time.time()

load(storage=storage)  # load cleverbot back from its previous state
verbosity('Configuration Loaded! CleverMe is now running!')


def main_loop(wdym_sent, energy, last_restore, last_ts, daemon=True):
    breakit = False
    while daemon or not breakit:
        newest_msg, newest_ts = newest_message(sc, slack_bot_id, slack_bot_user, slack_channel_id, last_ts)
        if newest_ts != last_ts:
            last_ts = newest_ts
            error, wdym_sent, result = cb_ask(newest_msg, wdym_sent)

            if not error:
                slack_message(result)
                save(storage=storage)  # save current conversation
                energy, last_restore = nap_time(energy, last_restore)
        else:
            time.sleep(1)

        if not daemon:
            breakit = True

try:
    if len(sys.argv) is 2:
        if '-d' in sys.argv[1]:
            verosity('Daemon is staring.', True, True)
            main_loop(wdym_sent, energy, last_restore, last_ts)
    else:
        verosity('Daemon is not running. Single run mode.', True, True)
        main_loop(wdym_sent, energy, last_restore, last_ts, True)
except KeyboardInterrupt:
   pass
except:
    verosity('Daemon is not running. Single run mode.', True, True)
    main_loop(wdym_sent, energy, last_restore, last_ts, True)
finally:
   del slack_bot_id, slack_bot_user, slack_channel_id, last_ts, wdym_sent, error, energy, last_restore
