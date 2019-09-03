import datetime
from flask import Flask, jsonify
from flask_cors import CORS

from config.config import Config

# db config
CONFIG = Config()
DB = CONFIG.db
COLLECT = DB["marketDB"]["fishPrice"]

# flask config
APP = Flask(__name__)
APP.config["SEND_FILE_MAX_AGE_DEFAULT"] = 1
CORS(APP, supports_credentials=True)


@APP.route("/fish/<start_date>/<end_date>", methods=["GET"])
def get_fishlist(start_date, end_date):
    """Filter the fish type that have been sold in the query interval.

    Args:
        start_date: The start date to query.
        end_date: The end date to query.

    Returns:
        A dict mapping keys to market name and values to the fish type that
        have been sold in the query interval in the market.
        For example:
        {
            all: [
                "白鯧",
                "黑鯛"
            ],
            台北: [
                "白鯧"
            ],
            佳里: [
                "黑鯛"
            ]
        }
    """
    # convert date string to int
    start_date = [int(x) for x in start_date.split("-")]
    end_date = [int(x) for x in end_date.split("-")]

    # build a pipeline that will return a list of fish that each market has sold
    market_pipeline = [
        {
            "$match": {
                "date": {
                    "$gte": datetime.datetime(
                        start_date[0], start_date[1], start_date[2], 0, 0, 1
                    ),
                    "$lte": datetime.datetime(
                        end_date[0], end_date[1], end_date[2], 23, 59, 59
                    ),
                }
            }
        },
        {"$group": {"_id": "$market", "fishList": {"$addToSet": "$name"}}},
    ]

    # build a pipeline that will return a list of fish that
    # "all" market has sold
    all_pipeline = [
        {
            "$match": {
                "date": {
                    "$gte": datetime.datetime(
                        start_date[0], start_date[1], start_date[2], 0, 0, 1
                    ),
                    "$lte": datetime.datetime(
                        end_date[0], end_date[1], end_date[2], 23, 59, 59
                    ),
                }
            }
        },
        {"$group": {"_id": None, "fishList": {"$addToSet": "$name"}}},
    ]

    # query
    market_fish = list(COLLECT.aggregate(market_pipeline))
    all_fish = list(COLLECT.aggregate(all_pipeline))

    # construct the result dict
    result = {}
    if len(all_fish) != 0:
        result["all"] = all_fish[0]["fishList"]
        for ele in market_fish:
            result[ele["_id"]] = ele["fishList"]

    return jsonify(result)


@APP.route("/fish/<date>/<market>/<fish_type>/price", methods=["GET"])
def oneday_data(date, market, fish_type):
    """Returns selling info on query date(one day).

    Args:
        date: The date to query.
        market: The market to query.
        fish_type: The fish type to query.

    Returns:
        A dict that mapping keys to market name and values to selling info
        of specific fish type on the query date in the query market.
        For example:
        {
            佳里: {
                price: 70,
                volume: 7
            }
        }
    """
    # convert date string to int
    date = [int(x) for x in date.split("-")]

    # build query pipeline
    if market == "all":
        query = {
            "date": datetime.datetime(date[0], date[1], date[2], 1, 0, 0),
            "name": fish_type,
        }
    else:
        query = {
            "date": datetime.datetime(date[0], date[1], date[2], 1, 0, 0),
            "name": fish_type,
            "market": market,
        }

    # query
    tmp = COLLECT.find(
        query, {"_id": 0, "market": 1, "volume": 1, "price.average": 1}
    )

    # construct the result
    result = {}
    for cur_data in tmp:
        result[cur_data["market"]] = {
            "price": cur_data["price"]["average"],
            "volume": cur_data["volume"],
        }
    return jsonify(result)


@APP.route(
    "/fish/<start_date>/<end_date>/<market>/<fish_type>/price", methods=["GET"]
)
def period_data(start_date, end_date, market, fish_type):
    """Returns selling info in query interval(period).

    Args:
        start_date: The start date to query.
        end_date: The end date to query.
        market: The market to query.
        fish_type: The fish type to query.

    Returns:
        A dict that mapping keys to market name and values to selling info
        of specific fish type in the query period in the query market.
        For example:
        {
            佳里: [
                {
                    date: "2019/07/02",
                    price: 70,
                    wolume: 7
                },
                {
                    date: "2019/07/03",
                    price: 15,
                    wolume: 17
                }
            ]
        }
    """
    # covert date string to int
    start_date = [int(x) for x in start_date.split("-")]
    end_date = [int(x) for x in end_date.split("-")]

    # build a pipeline that will return a list of detail data about
    # the fish that "all" market has sold from start_date to end_date
    if market == "all":
        pipeline = [
            {
                "$match": {
                    "date": {
                        "$gte": datetime.datetime(
                            start_date[0], start_date[1], start_date[2], 0, 0, 1
                        ),
                        "$lte": datetime.datetime(
                            end_date[0], end_date[1], end_date[2], 23, 59, 59
                        ),
                    },
                    "name": fish_type,
                }
            },
            {
                "$group": {
                    "_id": "$market",
                    "data": {
                        "$push": {
                            "date": {
                                "$dateToString": {
                                    "format": "%Y/%m/%d",
                                    "date": "$date",
                                }
                            },
                            "volume": "$volume",
                            "price": "$price.average",
                        }
                    },
                }
            },
        ]
    else:
        # build a pipeline that will return a list of detail data about
        # the fish that "target" market has sold from start_date to end_date
        pipeline = [
            {
                "$match": {
                    "date": {
                        "$gte": datetime.datetime(
                            start_date[0], start_date[1], start_date[2], 0, 0, 1
                        ),
                        "$lte": datetime.datetime(
                            end_date[0], end_date[1], end_date[2], 23, 59, 59
                        ),
                    },
                    "name": fish_type,
                    "market": market,
                }
            },
            {
                "$group": {
                    "_id": "$market",
                    "data": {
                        "$push": {
                            "date": {
                                "$dateToString": {
                                    "format": "%Y/%m/%d",
                                    "date": "$date",
                                }
                            },
                            "volume": "$volume",
                            "price": "$price.average",
                        }
                    },
                }
            },
        ]
    # query
    tmp = COLLECT.aggregate(pipeline)

    # construct result
    result = {}
    tmp = list(tmp)

    # add dumb data to make the result continous
    # let front end easily to make a continous line chart
    for elem in tmp:
        origin_len = len(elem["data"])

        start_date_datetime = datetime.datetime(
            start_date[0], start_date[1], start_date[2]
        )
        end_date_datetime = datetime.datetime(
            end_date[0], end_date[1], end_date[2]
        ) + datetime.timedelta(1)

        # zero_fill from start_date_datetime to elem["data"][0]["date"]
        cur_datetime = datetime.datetime.strptime(
            elem["data"][0]["date"], "%Y/%m/%d"
        )
        if cur_datetime - start_date_datetime != datetime.timedelta(0):
            zero_fill(elem, start_date_datetime, cur_datetime)

        # zero_fill from elem["data"][i-1]["date"] to elem["data"][i]["date"]
        for i in range(1, origin_len):
            cur_datetime = datetime.datetime.strptime(
                elem["data"][i]["date"], "%Y/%m/%d"
            )
            pre_datetime = datetime.datetime.strptime(
                elem["data"][i - 1]["date"], "%Y/%m/%d"
            )
            if cur_datetime - pre_datetime != datetime.timedelta(1):
                zero_fill(
                    elem, pre_datetime + datetime.timedelta(1), cur_datetime
                )

        # zero_fill from end_date_datetime to elem["data"][origin_len-1]["date"]
        cur_datetime = datetime.datetime.strptime(
            elem["data"][origin_len - 1]["date"], "%Y/%m/%d"
        )
        if end_date_datetime - cur_datetime != datetime.timedelta(1):
            zero_fill(elem, cur_datetime, end_date_datetime)

        elem["data"].sort(key=lambda d: d["date"])
        result[elem["_id"]] = elem["data"]
    return jsonify(result)


def zero_fill(elem, start_date, end_date):
    while start_date.date() != end_date.date():
        elem["data"].append(
            {"date": start_date.strftime("%Y/%m/%d"), "price": 0, "volume": 0}
        )
        start_date += datetime.timedelta(1)


if __name__ == "__main__":
    APP.run("0.0.0.0", 4011)
