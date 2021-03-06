#!/usr/bin/env python

import pickle
from time import sleep
import argparse
import io

from ytd import SymbolDownloader
from ytd.downloader.StockDownloader import StockDownloader
from ytd.downloader.ETFDownloader import ETFDownloader
from ytd.downloader.FutureDownloader import FutureDownloader
from ytd.downloader.IndexDownloader import IndexDownloader
from ytd.downloader.MutualFundDownloader import MutualFundDownloader
from ytd.downloader.CurrencyDownloader import CurrencyDownloader
from ytd.compat import text
from ytd.compat import csv
from reppy.robots import Robots

import tablib

import sys

user_agent = SymbolDownloader.user_agent

options = {
    "stocks": StockDownloader(),
    "etf": ETFDownloader(),
    "future": FutureDownloader(),
    "index": IndexDownloader(),
    "mutualfund": MutualFundDownloader(),
    "currency": CurrencyDownloader(),
}


def loadDownloader(tickerType):
    with open(tickerType + ".pickle", "rb") as f:
        return pickle.load(f)


def saveDownloader(downloader, tickerType):
    with open(tickerType + ".pickle", "wb") as f:
        pickle.dump(downloader, file=f, protocol=pickle.HIGHEST_PROTOCOL)


def downloadEverything(downloader, tickerType, insecure, sleeptime, pandantic, market):

    loop = 0
    while not downloader.isDone():

        symbols = downloader.nextRequest(insecure, pandantic, market)
        print("Got " + str(len(symbols)) + " downloaded " + downloader.type + " symbols:")
        if(len(symbols) > 2):
            try:
                print (" " + text(symbols[0]))
                print (" " + text(symbols[1]))
                print ("  ect...")
            except:
                print (" Could not display some ticker symbols due to char encoding")
        downloader.printProgress()

        # Save download state occasionally.
        # We do this in case this long running is suddenly interrupted.
        loop = loop + 1
        if loop % 200 == 0:
            print ("Saving downloader to disk...")
            saveDownloader(downloader, tickerType)
            print ("Downloader successfully saved.")
            print ("")

        if not downloader.isDone():
            sleep(sleeptime)  # So we don't overload the server.

def main():
    downloader = None

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--insecure", help="use HTTP instead of HTTPS", action="store_true")
    parser.add_argument("-e", "--export", help="export immediately without downloading (Only useful if you already downloaded something to the .pickle file)", action="store_true")
    parser.add_argument('-E', '--Exchange', help='Only export ticker symbols from this exchange (the filtering is done during the export phase)')
    parser.add_argument('type', help='The type to download, this can be: '+" ".join(list(options.keys())))
    parser.add_argument("-s", "--sleep", help="The time to sleep in seconds between requests", type=float, default=0)
    parser.add_argument("-p", "--pandantic", help="Stop and warn the user if some rare assertion fails", action="store_true")
    parser.add_argument("-m", "--market", help="Specify the Region of queried exchanges (us = USA+Canada, dr=Germany, fr=France, hk=Hongkong, gb=United Kingdom, default= all)", default="all")

    args = parser.parse_args()

    protocol = 'http' if args.insecure else 'https'
    if args.insecure:
        print("Using insecure connection")

    if args.export:
        print("Exporting pickle file")

    tickerType = args.type = args.type.lower()

    market = args.market = args.market.lower()

    print("Checking if we can resume a old download session")
    try:
        downloader = loadDownloader(tickerType)
        print("Downloader found on disk, resuming")
    except:
        print("No old downloader found on disk")
        print("Starting a new session")
        if tickerType not in options:
            print("Error: " + tickerType + " is not a valid type option. See --help")
            exit(1)
        else:
            downloader = options[tickerType]

    robots = Robots.fetch(protocol + '://finance.yahoo.com/robots.txt')
    try:
        if not args.export:
            
            if(not robots.allowed(protocol + '://finance.yahoo.com/_finance_doubledown/api/resource/finance.yfinlist.symbol_lookup', user_agent)):
                print("Robots.txt prevented downloading")
                return 1
            
            if not downloader.isDone():
                print("Downloading " + downloader.type)
                print("")
                downloadEverything(downloader, tickerType, args.insecure, args.sleep, args.pandantic, market)
                print ("Saving downloader to disk...")
                saveDownloader(downloader, tickerType)
                print ("Downloader successfully saved.")
                print ("")
            else:
                print("The downloader has already finished downloading everything")
                print("")

    except Exception as ex:
        print("A exception occurred while downloading. Suspending downloader to disk")
        saveDownloader(downloader, tickerType)
        print("Successfully saved download state")
        print("Try removing {type}.pickle file if this error persists")
        print("Issues can be reported on https://github.com/Benny-/Yahoo-ticker-symbol-downloader/issues")
        print("")
        raise
    except KeyboardInterrupt as ex:
        print("Suspending downloader to disk as .pickle file")
        saveDownloader(downloader, tickerType)

    if downloader.isDone() or args.export:
        print("Exporting "+downloader.type+" symbols")

        data = tablib.Dataset()
        data.headers = downloader.getRowHeader()

        for symbol in downloader.getCollectedSymbols():
            if(args.Exchange == None):
                data.append(symbol.getRow())
            elif (symbol.exchange == args.Exchange):
                data.append(symbol.getRow())

        with io.open(downloader.type + '.csv', 'w', encoding='utf-8') as f:
            f.write(text.join(u',', data.headers) + '\n')
            writer = csv.writer(f)
            for i in range(0, len(data)):
                row = [text(y) if not y is None else u"" for y in data[i]]
                writer.writerow(row)

        try:
            with open(downloader.type + '.xlsx', 'wb') as f:
                f.write(data.xlsx)
        except:
            print("Could not export .xlsx due to a internal error")

        try:
            with open(downloader.type + '.json', 'wb') as f:
                f.write(data.json.encode('UTF-8'))
        except:
            print("Could not export .json due to a internal error")

        try:
            with open(downloader.type + '.yaml', 'wb') as f:
                f.write(data.yaml.encode('UTF-8'))
        except:
            print("Could not export .yaml due to a internal error")

if __name__ == "__main__":
    main()
