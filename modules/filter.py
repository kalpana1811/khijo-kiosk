import json


def load_data():
    with open("data/users.json") as f:
        users = json.load(f)
    with open("data/menu.json") as f:
        menu = json.load(f)
    return users, menu


def get_all_dishes(menu):
    """Flatten menu into a simple list of dicts for easy filtering."""
    dishes = []
    for cat_key, cat in menu.items():
        for dish_id, dish in cat["items"].items():
            dishes.append({
                "id":       dish_id,
                "name":     dish["name"],
                "price":    dish["price"],
                "allergens":dish["allergens"],
                "avoid_tags":dish["avoid_tags"],
                "diet_tag": dish["diet_tag"],
                "halal":    dish["halal"],
                "category": cat["category_label"]
            })
    return dishes


def filter_menu(user, menu):
    """
    Returns (safe_dishes, removed_dishes) for a given user.

    A dish is removed if ANY of these are true:
      1. It contains an ingredient the user is allergic to
      2. Its avoid_tags overlap with the user's avoid list
      3. User prefers halal but dish is not halal
      4. User is vegetarian/vegan but dish is non-vegetarian
    """
    all_dishes    = get_all_dishes(menu)
    user_allergies = [a.lower() for a in user["allergies"]]
    user_avoid     = [a.lower() for a in user["avoid"]]
    user_prefs     = [p.lower() for p in user["dietary_preferences"]]

    safe    = []
    removed = []

    for dish in all_dishes:
        reason = _why_removed(dish, user_allergies, user_avoid, user_prefs)
        if reason:
            removed.append({**dish, "removed_reason": reason})
        else:
            safe.append(dish)

    return safe, removed


def _why_removed(dish, user_allergies, user_avoid, user_prefs):
    """
    Returns a reason string if the dish should be removed, else None.
    Checks in priority order: allergy → avoid → halal → diet.
    """

    # 1. Allergy check
    dish_allergens = [a.lower() for a in dish["allergens"]]
    for allergen in user_allergies:
        if allergen in dish_allergens:
            return f"contains allergen: {allergen}"

    # 2. Avoid check
    dish_avoid_tags = [t.lower() for t in dish["avoid_tags"]]
    for avoid_item in user_avoid:
        for tag in dish_avoid_tags:
            # partial match so "seafood" catches "prawns/seafood" etc.
            if avoid_item in tag or tag in avoid_item:
                return f"contains avoided ingredient: {avoid_item}"

    # 3. Halal check
    if "halal" in user_prefs and not dish["halal"]:
        return "not halal"

    # 4. Vegetarian check
    if "vegetarian" in user_prefs and dish["diet_tag"] == "non-vegetarian":
        return "not vegetarian"

    # 5. Vegan check
    if "vegan" in user_prefs and dish["diet_tag"] not in ("vegan",):
        return "not vegan"

    return None
