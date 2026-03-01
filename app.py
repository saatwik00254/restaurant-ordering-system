import razorpay
from flask import Flask, render_template, request, redirect, session
from flask import jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os


# MongoDB connection
from pymongo import MongoClient
import certifi


app = Flask(__name__)
app.secret_key = "secret123"



MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(
    MONGO_URI,
    tlsCAFile=certifi.where()
)

db = client["restaurantDB"]

menu_collection = db["menu"]
orders_collection = db["orders"]
users_collection = db["users"]



# ---------- AUTO INSERT MENU ITEMS ----------

# ---------- AUTO INSERT MENU ITEMS ----------

import base64

def seed_menu():

    menu_collection.delete_many({})

    items = [

        {
            "name": "Margherita Pizza",
            "price": 199,
            "image": "https://images.pexels.com/photos/825661/pexels-photo-825661.jpeg",
            "rating": 4.5
        },
        {
            "name": "Cheese Burger",
            "price": 149,
            "image": "https://images.pexels.com/photos/1639562/pexels-photo-1639562.jpeg",
            "rating": 4.7
        },
        {
            "name": "Masala Dosa",
            "price": 99,
            "image": "https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg",
            "rating": 4.4
        },
        {
            "name": "White Sauce Pasta",
            "price": 179,
            "image": "https://images.pexels.com/photos/1437267/pexels-photo-1437267.jpeg",
            "rating": 4.6
        },
        {
            "name": "Chocolate Ice Cream",
            "price": 89,
            "image": "https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg",
            "rating": 4.8
        },
        {
            "name": "French Fries",
            "price": 79,
            "image": "https://images.pexels.com/photos/1583884/pexels-photo-1583884.jpeg",
            "rating": 4.3
        },
        {
            "name": "Chicken Biryani",
            "price": 249,
            "image": "https://images.pexels.com/photos/9609838/pexels-photo-9609838.jpeg",
            "rating": 4.9
        },
        {
            "name": "Cold Coffee",
            "price": 129,
            "image": "https://images.pexels.com/photos/302899/pexels-photo-302899.jpeg",
            "rating": 4.2
        },
        {
            "name": "Chocolate Cake",
            "price": 159,
            "image": "https://images.pexels.com/photos/291528/pexels-photo-291528.jpeg",
            "rating": 4.7
        }
    ]

    menu_collection.insert_many(items)

    print("✅ Real food images inserted successfully!")


















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

    # calculate total
    total = sum(item["price"] * item["qty"] for item in cart)

    return render_template(
        "index.html",
        items=items,
        cart=cart,
        user=user,
        total=total
    )



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

    item = menu_collection.find_one({"_id": ObjectId(item_id)})

    if item is None:
        return redirect("/")

    cart = session.get("cart", [])

    found = False

    # increase quantity if already exists
    for c in cart:
        if c["name"] == item["name"]:
            c["qty"] += 1
            found = True
            break

    # add new item
    if not found:
        cart.append({
            "name": item["name"],
            "price": item["price"],
            "qty": 1
        })

    session["cart"] = cart
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


@app.route("/confirm_payment", methods=["POST"])
def confirm_payment():

    method = request.form["method"]
    cart = session.get("cart", [])

    if cart:
        orders_collection.insert_one({
            "user": session["user"],
            "items": cart,
            "payment_method": method,
            "payment_status": "Success",
            "order_status": "Preparing"
        })

        session["cart"] = []

    return render_template("payment_success.html")

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


@app.route("/api/menu")
def api_menu():
    items = list(menu_collection.find())

    for item in items:
        item["_id"] = str(item["_id"])

    return jsonify(items)






@app.route("/test")
def test():
    return "API WORKING"

# ---------- PAYMENT WEB SERVICE ----------

@app.route("/api/payment", methods=["POST"])
def api_payment():

    data = request.json

    order_id = orders_collection.insert_one({
        "user": data["user"],
        "items": data["items"],
        "payment_method": data["method"],
        "payment_status": "Success",
        "order_status": "Preparing"
    }).inserted_id

    return jsonify({
        "message": "Payment Successful",
        "order_id": str(order_id)
    })


@app.route("/api/payment_status/<order_id>")
def payment_status(order_id):

    order = orders_collection.find_one({"_id": ObjectId(order_id)})

    if order:
        return jsonify({
            "payment_status": order.get("payment_status", "Pending")
        })

    return jsonify({"payment_status": "Not Found"})




@app.route("/remove_item/<name>")
def remove_item(name):

    cart = session.get("cart", [])

    cart = [item for item in cart if item["name"] != name]

    session["cart"] = cart

    return redirect("/")







if __name__ == "__main__":
    seed_menu()   # 👈 AUTO LOAD MENU
    app.run(host="0.0.0.0", port=5000, debug=True)
