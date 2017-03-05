from cleverwrap import CleverWrap
from slackclient import SlackClient
import clever
import time
from random import random
from bisect import bisect
from config import *
import redis

sc = SlackClient(slack_token)
client = [CleverWrap(official_cleverbot), clever.CleverBot(user=cleverio_user, key=cleverio_key, nick=cleverio_nick)]
storage = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)


def slack_config():
    # getting channel ID
    channels = sc.api_call('channels.list')['channels']
    slack_channel_id = ''
    for channel in channels:
        if channel['name'] in slack_channel_name:
            slack_channel_id = channel['id']
    # getting bot id
    history = sc.api_call('channels.history', channel=slack_channel_id)
    slack_bot_id = ''
    for msg in history['messages']:
        try:
            if 'B' in msg['bot_id']:
                slack_bot_id = msg['bot_id']
        except:
            pass
    return slack_bot_id, slack_channel_id


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
    #try:
    cs, convo_id = client[0].save()
    storage.set('cs', cs)
    storage.set('convo_id', convo_id)
    #    return True
    #except:
    #    print("Error saving conversation information.")
    #    return False


def load(storage):
    try:
        cs = storage.get('cs')
        convo_id = storage.get('convo_id')
        client[0].load(cs=cs, convo_id=convo_id)
        return True
    except:
        print("Error loading previous conversation.")
        return False


def newest_message(sc, last_ts, slack_bot_id, slack_channel_id):
    msg_final = ''
    ts = 0
    while ts == 0:
        try:
            message = sc.api_call('channels.history', channel=slack_channel_id)
            for msg in message['messages']:
                # print(msg)
                try:
                    if msg['bot_id'] == slack_bot_id:
                        # print(msg)
                        pass
                    if msg['subtype'] == 'file_share':
                        msg_final = msg['file']['title']
                        ts = msg['ts']
                        break
                except:
                    msg_final = msg['text']
                    ts = msg['ts']
                    break
        except:
            print('Unable to get newest message from slack!')
            pass
        time.sleep(1)

    return msg_final, ts


def cb_ask(msg, wdym_sent):
    print('Asking: ' + msg)
    try:
        # id = weighted_choice([(0, 90), (1, 10)])
        id = 0
        result = 'I have not an answer for you...'
        error = False
        msg_wdym = 'You will have to explain things to me when I do not reply.'
        if id is 0:
            try:
                result = client[0].say(msg)
            except:
                result = client[1].query(msg)
                id = 1

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
        print('-error-: Having trouble thinking for myself!')
        return False, wdym_sent, "I'm having trouble thinking for myself."


def nap_time(energy, last_restore):
    energy -= 1
    if last_restore <= (time.time()-(60*60)):
        last_restore = time.time()
        energy = 100
    elif energy == 0:
        slack_message("brb")
        time.sleep(weighted_choice([(300, 5), (120, 15), (60, 25), (30, 50), (25, 25), (15, 5)]))
        slack_message("back")
        last_restore = time.time()
        energy = 100

    time.sleep(3)
    return energy, last_restore


def slack_message(message):
    print('Reply: ' + str(''.join(message)))
    sc.api_call("chat.postMessage", channel=slack_channel_name, text=str(''.join(message)))


slack_bot_id, slack_channel_id = slack_config()
last_ts = 0
wdym_sent = False
error = False
energy = 100
last_restore = time.time()

load(storage=storage)  # load cleverbot back from its previous state

while True:
    newest_msg, newest_ts = newest_message(sc, last_ts, slack_bot_id, slack_channel_id)
    if newest_ts != last_ts:
        last_ts = newest_ts
        error, wdym_sent, result = cb_ask(newest_msg, wdym_sent)

        if not error:
            slack_message(result)
            save(storage=storage)  # save current conversation
            energy, last_restore = nap_time(energy, last_restore)
    else:
        time.sleep(3)
