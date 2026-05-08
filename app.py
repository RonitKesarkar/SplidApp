from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import re
from sqlalchemy.dialects.postgresql import ARRAY

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost:5432/splid_app'
app.config['SECRET_KEY'] = 'secret'
db = SQLAlchemy(app)

# ---------------- MODELS ----------------

class Group(db.Model):
    __tablename__ = 'group'
    __table_args__ = {'schema': 'splid_app'}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20))
    type = db.Column(db.String(10))
    date = db.Column(db.DateTime(timezone=True))

class Member(db.Model):
    __tablename__ = 'member'
    __table_args__ = {'schema': 'splid_app'}

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('splid_app.group.id'))
    name = db.Column(db.String, nullable=False)
    paid = db.Column(db.Float, default=0)
    expense = db.Column(db.Float, default=0)
    balance = db.Column(db.Float, default=0)

class Expense(db.Model):
    __tablename__ = 'expense'
    __table_args__ = {'schema': 'splid_app'}

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('splid_app.group.id'))
    name = db.Column(db.String, nullable=False)
    amt = db.Column(db.Float, nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('splid_app.member.id'))
    paid_for = db.Column(ARRAY(db.Integer))
    date = db.Column(db.DateTime(timezone=True))

# ---------------- GROUP ----------------

@app.route('/', methods=['GET', 'POST'])
def create_group():
    if request.method == 'POST':
        db.session.add(Group(
            title=request.form["title"],
            type=request.form["type"],
            date=datetime.now(timezone.utc)
        ))
        db.session.commit()
        return redirect("/")
    return render_template("index.html", allGroups=Group.query.all())

@app.route('/enter_group/<int:id>', methods=['GET', 'POST'])
def enter_group(id):
    group = Group.query.get_or_404(id)
    if request.method == 'POST':
        group.title = request.form["title"]
        group.type = request.form["type"]
        db.session.commit()
        return redirect(f"/enter_group/{id}")
    members = Member.query.filter_by(group_id=id).all()
    expenses = Expense.query.filter_by(group_id=id).all()
    paid_by, paid_for = [], []
    for exp in expenses:
        payer = Member.query.get(exp.paid_by)
        paid_by.append(payer.name if payer else "Unknown")
        names = [
            Member.query.get(mid).name
            for mid in (exp.paid_for or [])
            if Member.query.get(mid)
        ]
        paid_for.append(names)
    return render_template(
        "group.html",
        group=group,
        members=members,
        expenses=expenses,
        paid_by=paid_by,
        paid_for=paid_for
    )

@app.route('/change_name/<int:id>', methods=['GET', 'POST'])
def change_name(id):
    group = Group.query.get_or_404(id)
    if request.method == 'POST':
        group.title = request.form["title"]
        group.type = request.form["type"]
        db.session.commit()
        return redirect(f"/enter_group/{id}")
    return render_template("update.html", group=group)

@app.route('/delete_group/<int:id>')
def delete_group(id):
    Expense.query.filter_by(group_id=id).delete()
    Member.query.filter_by(group_id=id).delete()
    Group.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect("/")

# ---------------- MEMBER ----------------

@app.route('/add_member/<int:id>', methods=['GET', 'POST'])
def add_member(id):
    if request.method == 'POST':
        name = request.form["name"]
        if Member.query.filter_by(name=name, group_id=id).first():
            flash("Member exists")
            return redirect(f"/enter_group/{id}")
        db.session.add(Member(name=name, group_id=id))
        db.session.commit()
        return redirect(f"/enter_group/{id}")
    return render_template("member.html", group=Group.query.get_or_404(id))

@app.route('/update_member/<int:id>', methods=['GET', 'POST'])
def update_member(id):
    m = Member.query.get_or_404(id)
    if request.method == 'POST':
        m.name = request.form["name"]
        db.session.commit()
        return redirect(f"/enter_group/{m.group_id}")
    return render_template("member_update.html", member=m, group=Group.query.get(m.group_id))

# ---------------- EXPENSE ----------------

@app.route('/add_expense/<int:id>', methods=['GET', 'POST'])
def add_expense(id):
    group = Group.query.get_or_404(id)
    members = Member.query.filter_by(group_id=id).all()
    if request.method == 'POST':
        try:
            name = request.form["name"]
            amt = round(float(request.form["amt"]), 2)
            payer = Member.query.filter_by(
                name=request.form["paid_by"],
                group_id=id
            ).first()
            if not payer:
                flash("Invalid payer")
                return redirect(f"/enter_group/{id}")
            paid_for = [
                m.id
                for k, v in request.form.items()
                if k.startswith("mem")
                for m in [Member.query.filter_by(name=v, group_id=id).first()]
                if m
            ]
            if not paid_for:
                flash("Select at least one member")
                return redirect(f"/enter_group/{id}")
            share = round(amt / len(paid_for), 2)
            payer.paid = round(payer.paid+amt, 2)
            payer.balance = round(payer.balance+amt, 2)
            for m in members:
                if m.id in paid_for:
                    m.expense = round(m.expense+share, 2)
                    m.balance = round(m.balance-share, 2)
            db.session.add(Expense(
                name=name,
                group_id=id,
                amt=amt,
                paid_by=payer.id,
                paid_for=paid_for,
                date=datetime.now(timezone.utc)
            ))
            db.session.commit()
            return redirect(f"/enter_group/{id}")
        except Exception:
            db.session.rollback()
            flash("Error adding expense")
            return redirect(f"/enter_group/{id}")
    return render_template("expense.html", group=group, members=members)

# ---------------- UPDATE EXPENSE ----------------

@app.route('/change_expense/<int:id>', methods=['GET', 'POST'])
def change_expense(id):
    exp = Expense.query.get_or_404(id)
    group = Group.query.get_or_404(exp.group_id)
    members = Member.query.filter_by(group_id=exp.group_id).all()
    if request.method == 'POST':
        try:
            old_payer = Member.query.get(exp.paid_by)
            if old_payer:
                old_payer.paid = round(old_payer.paid - exp.amt, 2)
                old_payer.balance = round(old_payer.balance - exp.amt, 2)
            old_share = round(exp.amt / len(exp.paid_for), 2) if exp.paid_for else 0
            for mid in (exp.paid_for or []):
                m = Member.query.get(mid)
                if m:
                    m.expense = round(m.expense - old_share, 2)
                    m.balance = round(m.balance + old_share, 2)
            amt = round(float(request.form["amt"]), 2)
            name = request.form["name"]
            paid_for = [
                m.id
                for k, v in request.form.items()
                if k.startswith("mem")
                for m in [Member.query.filter_by(name=v, group_id=exp.group_id).first()]
                if m
            ]
            if not paid_for:
                flash("Select at least one member")
                return redirect(f"/enter_group/{exp.group_id}")
            payer = Member.query.filter_by(
                name=request.form["paid_by"],
                group_id=exp.group_id
            ).first()
            share = round(amt / len(paid_for), 2)
            payer.paid = round(payer.paid + amt, 2)
            payer.balance = round(payer.balance + amt, 2)
            for m in members:
                if m.id in paid_for:
                    m.expense = round(m.expense + share, 2)
                    m.balance = round(m.balance - share, 2)
            exp.name = name
            exp.amt = amt
            exp.paid_by = payer.id
            exp.paid_for = paid_for
            db.session.commit()
            return redirect(f"/enter_group/{exp.group_id}")
        except Exception:
            db.session.rollback()
            flash("Update failed")
            return redirect(f"/enter_group/{exp.group_id}")
    return render_template("update_expense.html", expense=exp, group=group, members=members)

# ---------------- DELETE EXPENSE ----------------

@app.route('/delete_expense/<int:id>')
def delete_expense(id):
    exp = Expense.query.get_or_404(id)
    gid = exp.group_id
    payer = Member.query.get(exp.paid_by)
    if payer:
        payer.paid = round(payer.paid - exp.amt, 2)
        payer.balance = round(payer.balance - exp.amt, 2)
    share = round(exp.amt / len(exp.paid_for), 2) if exp.paid_for else 0
    for mid in (exp.paid_for or []):
        m = Member.query.get(mid)
        if m:
            m.expense = round(m.expense - share, 2)
            m.balance = round(m.balance + share, 2)
    db.session.delete(exp)
    db.session.commit()
    return redirect(f"/enter_group/{gid}")

# ---------------- SAVE PAYMENT ----------------

@app.route('/suggested_payments/<int:id>')
def suggested_payments(id):
    group = Group.query.get_or_404(id)
    members = Member.query.filter_by(group_id=id).all()
    creditors = []
    debtors = []
    for m in members:
        if m.balance > 0:
            creditors.append([m.id, m.name, round(m.balance, 2)])
        elif m.balance < 0:
            debtors.append([m.id, m.name, round(m.balance, 2)])
    i = 0
    j = 0
    payments = []
    while i < len(debtors) and j < len(creditors):
        did, dname, dbal = debtors[i]
        cid, cname, cbal = creditors[j]
        settle = round(min(-dbal, cbal), 2)
        payments.append([
            f"{dname} pays {settle} to {cname}",
            did,
            cid,
            settle
        ])
        debtors[i][2] = round(dbal + settle, 2)
        creditors[j][2] = round(cbal - settle, 2)
        if abs(debtors[i][2]) < 0.01:
            i += 1
        if abs(creditors[j][2]) < 0.01:
            j += 1
    return render_template(
        "suggested_payments.html",
        group=group,
        payments=payments
    )

@app.route('/save_payments/<payment>')
def save_payments(payment):
    pay = re.findall(r'\d+(?:\.\d+)?', payment)
    if len(pay) < 3:
        flash("Invalid payment")
        return redirect("/")
    amt = float(pay[0])
    payer = Member.query.get(int(pay[1]))
    receiver = Member.query.get(int(pay[2]))
    if not payer or not receiver:
        flash("Invalid users")
        return redirect("/")
    payer.balance = round(payer.balance + amt, 2)
    receiver.balance = round(receiver.balance - amt, 2)
    db.session.add_all([payer, receiver])
    db.session.add(Expense(
        group_id=payer.group_id,
        name="Settled up",
        amt=amt,
        paid_by=payer.id,
        paid_for=[receiver.id],
        date=datetime.now(timezone.utc)
    ))
    db.session.commit()
    return redirect(f"/enter_group/{payer.group_id}")

# ---------------- NAV ----------------

@app.route('/back_to_index')
def back_to_index():
    return render_template("index.html", allGroups=Group.query.all())

@app.route('/back_to_group/<int:id>')
def back_to_group(id):
    return redirect(f"/enter_group/{id}")

if __name__ == "__main__":
    app.run(debug=True)