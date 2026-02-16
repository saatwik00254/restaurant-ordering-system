from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "secret123"

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")

db = client["restaurantDB"]

menu_collection = db["menu"]
orders_collection = db["orders"]
users_collection = db["users"]


@app.route("/")
def home():
    query = request.args.get("q")

    if query:
        items = list(menu_collection.find({
            "name": {"$regex": query, "$options": "i"}
        }))
    else:
        items = list(menu_collection.find())

    cart = session.get("cart", [])
    user = session.get("user")
    return render_template("index.html", items=items, cart=cart, user=user)



# ---------- AUTH SYSTEM ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users_collection.insert_one({
            "username": username,
            "password": password
        })
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users_collection.find_one({
            "username": username,
            "password": password
        })

        if user:
            session["user"] = username
            return redirect("/")
        else:
            return "Invalid login"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------- CART ----------

@app.route("/add_to_cart/<item_id>")
def add_to_cart(item_id):
    from bson.objectid import ObjectId

    # find item safely
    item = menu_collection.find_one({"_id": ObjectId(item_id)})

    # if item missing → just go home (no crash)
    if item is None:
        return redirect("/")

    # create cart if not exists
    if "cart" not in session:
        session["cart"] = []

    # append safely
    session["cart"].append(item["name"])

    return redirect("/")






@app.route("/place_order")
def place_order():
    if "user" not in session:
        return redirect("/login")

    cart = session.get("cart", [])

    if cart:
        orders_collection.insert_one({
            "user": session["user"],
            "items": cart
        })
        session["cart"] = []

    return redirect("/")


# ---------- ADMIN DASHBOARD ----------

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("user") != "admin":
        return redirect("/login")

    # Add new food item
    if request.method == "POST":
        name = request.form["name"]
        price = int(request.form["price"])
        image = request.form["image"]

        menu_collection.insert_one({
            "name": name,
            "price": price,
            "image": image,
            "rating": 0
        })

    items = list(menu_collection.find())

    # ---------- STATISTICS ----------
    total_orders = orders_collection.count_documents({})
    revenue = sum(order.get("total", 0) for order in orders_collection.find())

    return render_template(
        "admin.html",
        items=items,
        total_orders=total_orders,
        revenue=revenue
    )

@app.route("/admin/orders")
def admin_orders():
    if session.get("user") != "admin":
        return redirect("/login")

    all_orders = list(orders_collection.find())
    return render_template("admin_orders.html", orders=all_orders)








# ---------- PAYMENT ----------

@app.route("/payment")
def payment():
    if "user" not in session:
        return redirect("/login")
    return render_template("payment.html")


@app.route("/confirm_payment")
def confirm_payment():
    cart = session.get("cart", [])
    if cart:
        orders_collection.insert_one({
            "user": session["user"],
            "items": cart,
            "status": "Paid"
        })
        session["cart"] = []
    return redirect("/")


@app.route("/rate/<item_id>/<int:rating>")
def rate(item_id, rating):
    menu_collection.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": {"rating": rating}}
    )
    return redirect("/")


# ---------- ORDER HISTORY ----------

@app.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login")

    user_orders = list(orders_collection.find({"user": session["user"]}))
    return render_template("orders.html", orders=user_orders)







if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
