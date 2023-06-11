import aiohttp
import argparse
import asyncio
import datetime
import json
import platform
from collections import defaultdict

async def get_cur_rates(session, date:str, currencies: list):

    async with session.get(f'https://api.privatbank.ua/p24api/exchange_rates?json&date={date}') as response:
       json_ = await response.text()
       data = json.loads(json_)
    try:
        currencies_collected = [cur for cur in data['exchangeRate'] if cur['currency'] in currencies]
    except KeyError:
        yesterday = datetime.datetime.strptime(date, '%d.%m.%Y') - datetime.timedelta(days=1)
        y_date = yesterday.strftime('%d.%m.%Y')
        async with session.get(f'https://api.privatbank.ua/p24api/exchange_rates?json&date={y_date}') as response:
            json_ = await response.text()
            data = json.loads(json_)
    finally:
        currencies_collected = [cur for cur in data['exchangeRate'] if cur['currency'] in currencies]

        result = defaultdict(dict)

        for entry in currencies_collected:
            currency = entry["currency"]
            sale_rate = entry["saleRateNB"]
            purchase_rate = entry["purchaseRateNB"]
            result[date][currency] = {"sale": sale_rate, "purchase": purchase_rate}
        result = dict(result)

        return result


async def collect_cur_rates(days: int, currencies: list) -> list:
    today = datetime.datetime.now().date()
    async with aiohttp.ClientSession() as session:
        results = []
        requests = []
        for d in range(0, days if days <= 10 else 10):
            date = today.replace(day=(today.day - d)).strftime('%d.%m.%Y')
            request = asyncio.create_task(get_cur_rates(session, date, currencies))
            requests.append(request)
            results = await asyncio.gather(*requests)

        return results

def format_output(raw_out:list) -> str:
    out_str = ''
    for day in raw_out:
        date = list(day.keys())[0]
        print(date)
        out_str += date + "\n"
        for cur in day[date].keys():
            out_str += f"{cur}: Sale:{day[date][cur]['sale']}; Purchase: {day[date][cur]['purchase']} \n"

    return out_str


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Currency exchanges")
    parser.add_argument("days", help="days before today (10 days max)", type=int, default=1)
    parser.add_argument("--currencies", "-cur", help="""Currency codes, separated by comas. 
Default USD, EUR. Available also:
Australian Dollar (AUD)
Azerbaijani Manat (AZN)
Belarusian Ruble (BYN)
Canadian Dollar (CAD)
Swiss Franc (CHF)
Chinese Yuan (CNY)
Czech Koruna (CZK)
Danish Krone (DKK)
British Pound (GBP)
Georgian Lari (GEL)
Hungarian Forint (HUF)
Israeli Shekel (ILS)
Japanese Yen (JPY)
Kazakhstani Tenge (KZT)
Moldovan Leu (MDL)
Norwegian Krone (NOK)
Polish Złoty (PLN)
Swedish Krona (SEK)
Singapore Dollar (SGD)
Turkmenistani Manat (TMT)
Turkish Lira (TRY)
Ukrainian Hryvnia (UAH)
Uzbekistani Som (UZS)
Gold Ounce (XAU) """,
                        default=['USD', 'EUR'], nargs='+', required=False)
    args = vars(parser.parse_args())
    print(args)
    days = args['days']
    curr = args['currencies']
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    output = asyncio.run(collect_cur_rates(days=days, currencies=curr))
    if days > 10:
        print('Sorry, max 10 past days data is available!')
    print(format_output(output))
