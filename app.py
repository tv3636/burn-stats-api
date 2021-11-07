from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS, cross_origin
from collections import defaultdict
import requests, csv, json

resultJson = []
burned = 0
flames = 1112

def getStats():
	global resultJson
	global burned

	pageSize = 50
	nextPageSize = 50
	burnedWizards = []

	traitDict = defaultdict(list)
	originalTraitCounts = defaultdict(lambda: defaultdict(int))
	newTraitCounts = defaultdict(lambda: defaultdict(int))

	traits = ['head', 'body', 'prop', 'familiar', 'rune', 'background']
	nullAddress = "0x0000000000000000000000000000000000000000"
	wizardsContractAddress = "0x521f9c7505005cfa19a8e5786a9c3c9c9f5e6f42"
	url = "https://api.opensea.io/api/v1/assets?owner=%s&asset_contract_addresses=%s&order_direction=desc&offset=%%s&limit=%d" % (nullAddress, wizardsContractAddress, nextPageSize)

	while nextPageSize == pageSize:
		wizards = requests.request("GET", url % str(len(burnedWizards))).json()['assets']

		for wizard in wizards:
			burnedWizards.append(wizard['token_id'])

			for trait in wizard['traits']:
				if trait['trait_type'] != 'Serial':
					traitDict[trait['trait_type'] + '_' + trait['value']].append(wizard['token_id'])

		nextPageSize = len(wizards)

	burned = len(burnedWizards)
	print(burned)

	with open('wizards.csv') as csvfile:
		for wizard in csv.DictReader(csvfile):
			for trait in traits:
				originalTraitCounts[trait][wizard[trait]] += 1

				if wizard['token_id'] not in burnedWizards:
					newTraitCounts[trait][wizard[trait]] += 1


	output = []

	for trait in traits:
		for value in originalTraitCounts[trait]:
			output.append({
				'type': trait,
				'name': value,
				'old': originalTraitCounts[trait][value],
				'new': newTraitCounts[trait][value],
				'diff': originalTraitCounts[trait][value] - newTraitCounts[trait][value],
				'wizards': traitDict[trait + '_' + value]
			})

	print('success')

	resultJson = sorted(output, key= lambda i: i['diff'], reverse=True)

	# hacky workaround to keep the app running since it dies after some time with no requests
	requests.get("https://aqueous-eyrie-64590.herokuapp.com/api/get")


sched = BackgroundScheduler(daemon=True)
sched.add_job(getStats,'interval', minutes=5, next_run_time=datetime.now())
sched.start()

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route("/api/get")
@cross_origin()
def home():
    return {'traits': resultJson, 'burned': burned, 'flames': flames - burned}

if __name__ == "__main__":
    app.run()
