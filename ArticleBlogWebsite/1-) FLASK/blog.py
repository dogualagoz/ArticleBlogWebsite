from flask import Flask, render_template, flash, redirect, url_for, session, request, g, request
import pymysql
from pymysql.cursors import DictCursor
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import email_validator
from functools import wraps

app = Flask(__name__)
app.secret_key = "dogublog"

# Veritabanı bağlantısı için gserekli bilgiler
db_connection = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'db': 'dogublog',
    'cursorclass': DictCursor,
    'unix_socket': '/Applications/MAMP/tmp/mysql/mysql.sock'
}

def get_db_connection():
    return pymysql.connect(**db_connection)


def login_required(f): # Sadece giriş yapılınca girebileceğimiz kısımlar için kullanılır. @login_required koymamı yetiyor
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if "logged_in" in session:
            return f(*args,**kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın","danger")
            return redirect(url_for("login"))
    return decorated_function  


# TODO KULLANICI KAYIT FORMU
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.Length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=3, max=30)])
    email = StringField("E-Posta", validators=[validators.Email(message="Geçersiz Email")])
    password = PasswordField("Parola: ", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname="confirm", message="Parolanız Uyuşmuyor")
    ])
    confirm = PasswordField("Parola doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı: ")
    password = PasswordField("Şifre: ")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
        connection = get_db_connection()
        cursor = connection.cursor()
        
        sorgu = "Select * From articles"
        result = cursor.execute(sorgu)

        if result > 0:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)

        else:
            return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    connection = get_db_connection()
    cursor = connection.cursor()

    sorgu = "Select * From articles where author = %s"
    result = cursor.execute(sorgu,{session["username"],})

    if result > 0 :
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")


    return render_template("dashboard.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.hash(form.password.data)

        connection = get_db_connection()
        cursor = connection.cursor()

        sorgu = "INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)"
        cursor.execute(sorgu, (name, email, username, password))
        connection.commit()

        cursor.close()
        connection.close()
        flash("Başarıyla Kayıt Oldunuz...", "success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        connection = get_db_connection()
        cursor = connection.cursor()

        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu, (username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash("Başarıyla Giriş Yaptınız...", "success")
                 
                session["logged_in"] = True
                session["username"] = username 

                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Girdiniz....", "danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor...", "danger")
            return redirect(url_for("login"))

        cursor.close()
        connection.close()

    return render_template("login.html", form=form)

# Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    connection = get_db_connection()
    cursor = connection.cursor()
    sorgu = "Select * from articles where id = %s"

    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    
    else:
        return render_template("article.html")


# Logout İşlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Makale Ekleme

@app.route("/addarticle",methods= ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        connection = get_db_connection()
        cursor = connection.cursor()

        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))

        connection.commit()
        cursor.close()
        connection.close()

        flash("Makale başarıyla eklendi","success")
        return redirect(url_for("dashboard"))


    return render_template("addarticle.html",form= form)


#Makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    connection = get_db_connection()
    cursor = connection.cursor()

    sorgu = "Select * from articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"

        cursor.execute(sorgu2,(id,))

        connection.commit()

        return redirect(url_for("dashboard"))
        

    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))

# Makale Güncelleme

@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        connection = get_db_connection()
        cursor = connection.cursor()

        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok ","danger")
            return redirect(url_for("index"))
        
        
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
            

    else:
        # POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "Update articles Set title = %s, content = %s where id = %s"

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))

        connection.commit()

        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))



#Makale Form

class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.length(min= 5,max = 100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.length(min=10)])


# Arama URL

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    
    else:
        keyword = request.form.get("keyword")

        connection = get_db_connection()
        cursor = connection.cursor()

        sorgu = "Select * from articles where title like '%" + keyword + "%' "

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles=articles)
        

if __name__ == "__main__":
    app.run(debug=True, port=5001)

