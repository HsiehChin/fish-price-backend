import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

import time
from config.config import Config

CONFIG = Config()
DB = CONFIG.db
COLLECT = DB["marketDB"]["fishPrice"]

APP = Flask(__name__)
APP.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1
CORS(APP, supports_credentials=True)


@APP.route("/get_fishlist", methods=["POST"])
def get_fishlist():
    # get start_date & end_date, covert them into int
    start_date = request.get_json(force=True).get("startDate").split("-")
    start_date = [int(x) for x in start_date]
    end_date = request.get_json(force=True).get("endDate").split("-")
    end_date = [int(x) for x in end_date]

    # build a pipeline that will return a list of fish that each market has sold
    market_pipeline = [
        {
            "$match": {
                "date": {
                    "$gte": datetime.datetime(start_date[0], start_date[1], start_date[2], 0, 0, 1),
                    "$lte": datetime.datetime(end_date[0], end_date[1], end_date[2], 23, 59, 59)
                }
            }
        },
        {
            "$group": {
                "_id": "$market",
                "fishList": {"$addToSet": "$name"}
            }
        }
    ]
    # build a pipeline that will return a list of fish that "all" market has sold
    all_pipeline = [
        {
            "$match": {
                "date": {
                    "$gte": datetime.datetime(start_date[0], start_date[1], start_date[2], 0, 0, 1),
                    "$lte": datetime.datetime(end_date[0], end_date[1], end_date[2], 23, 59, 59)
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "fishList": {"$addToSet": "$name"}
            }
        }
    ]

    # start query and construct the result dict
    market_fish = list(COLLECT.aggregate(market_pipeline))
    all_fish = list(COLLECT.aggregate(all_pipeline))
    result = {}
    if len(all_fish) != 0:
        result["all"] = all_fish[0]["fishList"]
        for ele in market_fish:
            result[ele["_id"]] = ele["fishList"]

    return jsonify(result)


@APP.route("/oneday_data", methods=["POST"])
def oneday_data():
    # get the query date
    data = request.get_json(force=True)
    date = [int(x) for x in data["date"].split("-")]
    if data["market"] == "all":
        query = {
            "date": datetime.datetime(date[0], date[1], date[2], 1, 0, 0),
            "name": data["name"]
        }
    else:
        query = {
            "date": datetime.datetime(date[0], date[1], date[2], 1, 0, 0),
            "name": data["name"],
            "market": data["market"]
        }
    tmp = COLLECT.find(query, {"_id": 0, "market": 1,
                               "volume": 1, "price.average": 1})
    result = {}
    for cur_data in tmp:
        result[cur_data["market"]] = {
            "price": cur_data["price"]["average"],
            "volume": cur_data["volume"]
        }
    return jsonify(result)


@APP.route("/period_data", methods=["POST"])
def period_data():
    # get start_date & end_date, covert them into int
    cal_start_time = time.time()
    data = request.get_json(force=True)
    start_date = [int(x) for x in data["startDate"].split("-")]
    end_date = [int(x) for x in data["endDate"].split("-")]

    # build a pipeline that will return a list of detail data about the fish that "all" market has sold from start_date to end_date
    if data["market"] == "all":
        pipeline = [
            {
                '$match': {
                    'date': {
                        '$gte': datetime.datetime(start_date[0], start_date[1], start_date[2], 0, 0, 1),
                        '$lte': datetime.datetime(end_date[0], end_date[1], end_date[2], 23, 59, 59)
                    },
                    'name': data["name"]
                }
            }, {
                '$group': {
                    '_id': '$market',
                    'data': {
                        '$push': {
                            'date': {
                                '$dateToString': {
                                    'format': '%Y/%m/%d',
                                    'date': '$date'
                                }
                            },
                            'volume': '$volume',
                            'price': '$price.average'
                        }
                    }
                }
            }
        ]
    else:
        # build a pipeline that will return a list of detail data about the fish that "target" market has sold from start_date to end_date
        pipeline = [
            {
                '$match': {
                    'date': {
                        '$gte': datetime.datetime(start_date[0], start_date[1], start_date[2], 0, 0, 1),
                        '$lte': datetime.datetime(end_date[0], end_date[1], end_date[2], 23, 59, 59)
                    },
                    'name': data["name"],
                    'market': data["market"]
                }
            }, {
                '$group': {
                    '_id': '$market',
                    'data': {
                        '$push': {
                            'date': {
                                '$dateToString': {
                                    'format': '%Y/%m/%d',
                                    'date': '$date'
                                }
                            },
                            'volume': '$volume',
                            'price': '$price.average'
                        }
                    }
                }
            }
        ]
    tmp = COLLECT.aggregate(pipeline)
    result = {}
    tmp = list(tmp)
    cal_end_time = time.time()
    print("cost time", cal_end_time - cal_start_time)

    # add dumb data to make the result continous
    for elem in tmp:
        origin_len = len(elem["data"])

        start_date_datetime = datetime.datetime(
            start_date[0], start_date[1], start_date[2])
        end_date_datetime = datetime.datetime(
            end_date[0], end_date[1], end_date[2]) + datetime.timedelta(1)

        # zero_fill from start_date_datetime to elem["data"][0]["date"]
        cur_datetime = datetime.datetime.strptime(
            elem["data"][0]["date"], "%Y/%m/%d")
        if cur_datetime - start_date_datetime != datetime.timedelta(0):
            zero_fill(elem, start_date_datetime, cur_datetime)

        # zero_fill from elem["data"][i-1]["date"] to elem["data"][i]["date"]
        for i in range(1, origin_len):
            cur_datetime = datetime.datetime.strptime(
                elem["data"][i]["date"], "%Y/%m/%d")
            pre_datetime = datetime.datetime.strptime(
                elem["data"][i - 1]["date"], "%Y/%m/%d")
            if cur_datetime - pre_datetime != datetime.timedelta(1):
                zero_fill(elem, pre_datetime + datetime.timedelta(1), cur_datetime)

        # zero_fill from end_date_datetime to elem["data"][origin_len-1]["date"]
        cur_datetime = datetime.datetime.strptime(
            elem["data"][origin_len - 1]["date"], "%Y/%m/%d")
        if end_date_datetime - cur_datetime != datetime.timedelta(1):
            zero_fill(elem, cur_datetime, end_date_datetime)

        elem["data"].sort(key=lambda d: d["date"])
        result[elem["_id"]] = elem["data"]
    return jsonify(result)

# let front end easily to make a continous line chart


def zero_fill(elem, start_date, end_date):
    while start_date.date() != end_date.date():
        elem["data"].append({
            "date": start_date.strftime("%Y/%m/%d"),
            "price": 0,
            "volume": 0
        })
        start_date += datetime.timedelta(1)


if __name__ == "__main__":
    APP.run('0.0.0.0', 4010)
