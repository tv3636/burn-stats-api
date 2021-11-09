from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS, cross_origin
from collections import defaultdict
import requests, csv, json

traits = ['head', 'body', 'prop', 'familiar', 'rune', 'background']
nullAddress = "0x0000000000000000000000000000000000000000"
wizardsContractAddress = "0x521f9c7505005cfa19a8e5786a9c3c9c9f5e6f42"
soulsContractAddress = "0x251b5f14a825c537ff788604ea1b58e49b70726f"

resultJson = []
burnOrder = {}
soulTraits = {}
burned = 0
flames = 1112

def getStats():
	global resultJson
	global burned
	global burnOrder
	global soulTraits

	try:
		pageSize = 50
		nextPageSize = 50
		burnedWizards = []
		traitDict = defaultdict(list)
		originalTraitCounts = defaultdict(lambda: defaultdict(int))
		newTraitCounts = defaultdict(lambda: defaultdict(int))
		newOrder = {}

		url = "https://api.opensea.io/api/v1/assets?owner=%s&asset_contract_addresses=%s&order_direction=desc&offset=%%s&limit=%d" % (nullAddress, wizardsContractAddress, nextPageSize)

		# Pull original traits from Forgotten Runes collection
		while nextPageSize == pageSize:
			wizards = requests.request("GET", url % str(len(burnedWizards))).json()['assets']

			for wizard in wizards:
				burnedWizards.append(wizard['token_id'])

				for trait in wizard['traits']:
					if trait['trait_type'] != 'Serial':
						traitDict[trait['trait_type'] + '_' + trait['value']].append(wizard['token_id'])

			nextPageSize = len(wizards)

		burned = len(burnedWizards)

		# Pull burn order from Forgotten Souls collection
		pageSize = 50
		nextPageSize = 50

		url = "https://api.opensea.io/api/v1/assets?asset_contract_addresses=%s&order_direction=desc&offset=%%s&limit=%d" % (soulsContractAddress, nextPageSize)

		while nextPageSize == pageSize:
			souls = requests.request("GET", url % str(len(newOrder))).json()['assets']

			for soul in souls:
				soulTraits[soul['token_id']] = {'name': soul['name'], 'traits': {}}

				for trait in soul['traits']:
					if trait['trait_type'] == 'Burn order':
						newOrder[soul['token_id']] = int(trait['value'])
					elif trait['trait_type'].lower() == trait['trait_type']:
						soulTraits[soul['token_id']]['traits'][trait['trait_type']] = trait['value']

			nextPageSize = len(souls)

		print(len(newOrder))
		burnOrder = newOrder

		# Get original trait counts from Forgotten Runes csv
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

		resultJson = sorted(output, key= lambda i: i['name'])

		# hacky workaround to keep the app running since it dies after some time with no requests
		requests.get("https://aqueous-eyrie-64590.herokuapp.com/api/get")

	except Exception as e:
		print(e)


sched = BackgroundScheduler(daemon=True)
sched.add_job(getStats,'interval', minutes=5, next_run_time=datetime.now())
sched.start()

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route("/api/get")
@cross_origin()
def home():
	global burnOrder

	return {
		'traits': resultJson, 
		'burned': burned, 
		'flames': flames - burned, 
		'order': [k for k, v in sorted(burnOrder.items(), key=lambda item: item[1], reverse=True)],
		'souls': soulTraits
	}

if __name__ == "__main__":
	app.run()
