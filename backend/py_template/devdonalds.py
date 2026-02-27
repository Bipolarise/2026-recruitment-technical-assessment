from dataclasses import dataclass
from typing import List, Dict, Union
from flask import Flask, request, jsonify
import re

# ==== Type Definitions, feel free to add or modify ===========================
@dataclass
class CookbookEntry:
	name: str

@dataclass
class RequiredItem():
	name: str
	quantity: int

@dataclass
class Recipe(CookbookEntry):
	required_items: List[RequiredItem]

@dataclass
class Ingredient(CookbookEntry):
	cook_time: int


# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
cookbook: Dict[str, Union[Recipe, Ingredient]] = {}

# task 1 helper
@app.route("/parse", methods=['POST'])
def parse():
	data = request.get_json()
	recipe_name = data.get('input', '')
	parsed_name = parse_handwriting(recipe_name)
	if parsed_name is None:
		return 'Invalid recipe name', 400
	return jsonify({'msg': parsed_name}), 200

# [TASK 1] ====================================================================
def parse_handwriting(recipeName: str) -> Union[str | None]:
	# replace hyphens/underscores with spaces
	s = recipeName.replace('-', ' ').replace('_', ' ')

	# remove anything that's not a letter or whitespace
	s = re.sub(r'[^A-Za-z\s]', '', s)

	# squash multiple whitespace to a single space + trim ends
	s = re.sub(r'\s+', ' ', s).strip()

	# must be non-empty
	if len(s) == 0:
		return None

	# capitalise first letter of each word rest lowercase
	words = s.split(' ')
	words = [w[:1].upper() + w[1:].lower() if w else '' for w in words]
	return ' '.join(words)

# [TASK 2] ====================================================================
# Endpoint that adds a CookbookEntry to your magical cookbook
@app.route('/entry', methods=['POST'])
def create_entry():
	global cookbook

	try:
		data = request.get_json(silent=True)
		if not isinstance(data, dict):
			return '', 400

		# autotester likely sends entry directly, but we also support {"entry": {...}}
		entry = data.get('entry') if isinstance(data.get('entry'), dict) else data
		if not isinstance(entry, dict):
			return '', 400

		entry_type = entry.get('type')
		name = entry.get('name')

		# type can only be "recipe" or "ingredient"
		if entry_type not in ('recipe', 'ingredient'):
			return '', 400

		# name must be a non-empty string
		if not isinstance(name, str) or len(name.strip()) == 0:
			return '', 400

		# entry names must be unique
		if name in cookbook:
			return '', 400

		if entry_type == 'ingredient':
			cook_time = entry.get('cookTime')

			# cookTime >= 0
			if not isinstance(cook_time, int) or cook_time < 0:
				return '', 400

			cookbook[name] = Ingredient(name=name, cook_time=cook_time)
			return jsonify({}), 200

		# recipe
		required_items = entry.get('requiredItems')
		if not isinstance(required_items, list):
			return '', 400

		seen_names = set()
		parsed_items: List[RequiredItem] = []

		for item in required_items:
			if not isinstance(item, dict):
				return '', 400

			item_name = item.get('name')
			quantity = item.get('quantity')

			if not isinstance(item_name, str) or len(item_name.strip()) == 0:
				return '', 400
			if not isinstance(quantity, int):
				return '', 400

			# requiredItems can only have one element per name
			if item_name in seen_names:
				return '', 400
			seen_names.add(item_name)

			parsed_items.append(RequiredItem(name=item_name, quantity=quantity))

		cookbook[name] = Recipe(name=name, required_items=parsed_items)
		return jsonify({}), 200

	except Exception:
		# never crash the server for malformed requests
		return '', 400

# [TASK 3] ====================================================================
def _expand_to_ingredients(entry_name: str, multiplier: int, acc: Dict[str, int]) -> int:
	"""
	Returns total cook time contributed by expanding entry_name * multiplier.
	Accumulates base ingredient quantities into acc.
	Raises KeyError/ValueError for missing entries or invalid structure.
	"""
	if entry_name not in cookbook:
		raise KeyError("missing entry")

	entry = cookbook[entry_name]

	# ingredient leaf
	if isinstance(entry, Ingredient):
		acc[entry.name] = acc.get(entry.name, 0) + multiplier
		return entry.cook_time * multiplier

	# recipe node
	if isinstance(entry, Recipe):
		total = 0
		for req in entry.required_items:
			# quantity must be int (task 2 already enforces) but being safe frfr
			if not isinstance(req.quantity, int):
				raise ValueError("bad quantity")
			total += _expand_to_ingredients(req.name, multiplier * req.quantity, acc)
		return total

	raise ValueError("unknown entry type")

@app.route('/summary', methods=['GET'])
def summary():
	try:
		name = request.args.get('name', type=str)
		if not name or len(name.strip()) == 0:
			return '', 400

		# must exist
		if name not in cookbook:
			return '', 400

		# must be a recipe, not an ingredient
		if isinstance(cookbook[name], Ingredient):
			return '', 400

		if not isinstance(cookbook[name], Recipe):
			return '', 400

		# expand recursively
		acc: Dict[str, int] = {}
		total_time = _expand_to_ingredients(name, 1, acc)

		ingredients_list = [{'name': ing_name, 'quantity': qty} for ing_name, qty in acc.items()]
		return jsonify({
			'name': name,
			'cookTime': total_time,
			'ingredients': ingredients_list
		}), 200

	except Exception:
		return '', 400

# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, host="::", port=8080)
