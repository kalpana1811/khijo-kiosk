from collections import Counter
from datetime import datetime
from modules.filter import filter_menu, get_all_dishes

WEIGHT_HISTORY    = 5
WEIGHT_PREF_MATCH = 4
WEIGHT_TIME       = 3

DRINK_CATEGORIES  = {"Drinks"}
SIDE_CATEGORIES   = {"Sides"}

# Time-based category boosts
# Morning  <12:00  → light: Sides, Drinks, Momo Buns
# Afternoon 12-17  → mains: Noodle Soup, Yakisoba, Japanese Rice Bowl, Sets
# Evening  >17:00  → heavier: Hotpot, Sets, Japanese Rice Bowl
TIME_BOOSTS = {
    "morning":   {"Sides", "Drinks", "Momo Buns"},
    "afternoon": {"Noodle Soup", "Yakisoba", "Japanese Rice Bowl", "Sets"},
    "evening":   {"Hotpot", "Sets", "Japanese Rice Bowl"},
}

PREF_BOOST_RULES = {
    "high protein":  lambda dish: dish["diet_tag"] == "non-vegetarian",
    "low calorie":   lambda dish: dish["price"] <= 8.50,
    "vegetarian":    lambda dish: dish["diet_tag"] in ("vegetarian", "vegan"),
    "vegan":         lambda dish: dish["diet_tag"] == "vegan",
    "halal":         lambda dish: dish["halal"],
    "gluten-free":   lambda dish: "gluten" not in [a.lower() for a in dish["allergens"]],
}


def get_time_of_day():
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    else:
        return "evening"


def score_dish(dish, user, history_counter, time_of_day):
    score = 0

    # Deprioritise drinks/sides in main recs
    if dish["category"] in DRINK_CATEGORIES:
        score -= 20
    if dish["category"] in SIDE_CATEGORIES:
        score -= 5

    # Time of day boost
    boosted_cats = TIME_BOOSTS.get(time_of_day, set())
    if dish["category"] in boosted_cats:
        score += WEIGHT_TIME

    # Order history boost
    score += history_counter.get(dish["name"], 0) * WEIGHT_HISTORY

    # Diet preference boosts
    for pref in user["dietary_preferences"]:
        pref_lower = pref.lower()
        if pref_lower in PREF_BOOST_RULES:
            if PREF_BOOST_RULES[pref_lower](dish):
                score += WEIGHT_PREF_MATCH

    
    score -= dish["price"] * 0.1

    return round(score, 2)


def get_recommendations(user, menu, top_n=3):
    """Returns top N safe dishes — time-aware + history + preference scored."""
    safe, _ = filter_menu(user, menu)
    history_counter = Counter(user["order_history"])
    time_of_day = get_time_of_day()

    # Only score main dishes (not drinks/sides) for recommendations
    main_dishes = [d for d in safe
                   if d["category"] not in DRINK_CATEGORIES | SIDE_CATEGORIES]

    scored = []
    for dish in main_dishes:
        s = score_dish(dish, user, history_counter, time_of_day)
        scored.append((s, dish))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(dish, score) for score, dish in scored[:top_n]]


def get_surprise(user, menu):
    """Returns a random safe main dish the user hasn't ordered before."""
    import random
    safe, _ = filter_menu(user, menu)
    main_dishes = [d for d in safe if d["category"] not in DRINK_CATEGORIES]
    history_set = set(user["order_history"])
    new_dishes  = [d for d in main_dishes if d["name"] not in history_set]
    if not new_dishes:
        new_dishes = main_dishes
    return random.choice(new_dishes) if new_dishes else None


def get_healthy_options(user, menu, top_n=3):
    """Returns cheapest safe main dishes."""
    safe, _ = filter_menu(user, menu)
    main_dishes = [d for d in safe if d["category"] not in DRINK_CATEGORIES]
    return sorted(main_dishes, key=lambda d: d["price"])[:top_n]


def get_last_order(user, menu):
    """Returns most recent safe dish from order history."""
    all_dishes  = get_all_dishes(menu)
    dish_lookup = {d["name"]: d for d in all_dishes}
    safe, _     = filter_menu(user, menu)
    safe_names  = {d["name"] for d in safe}

    for dish_name in reversed(user["order_history"]):
        if dish_name in safe_names and dish_name in dish_lookup:
            return dish_lookup[dish_name]
    return None
