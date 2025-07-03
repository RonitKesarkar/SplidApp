from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = "secret key"
app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///groups.db"
app.config['SQLALCHEMY_BINDS']={"members":"sqlite:///members.db",
                                "expenses":"sqlite:///expenses.db"}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)

class Group(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(200), nullable=False)
    type=db.Column(db.String(200), nullable=False)
    date=db.Column(db.String, default=datetime.now().strftime("%d %b %X"))

    def __repr__(self)->str:
        return f"{self.id} - {self.title}"

class Member(db.Model):
    __bind_key__="members"
    id=db.Column(db.Integer, primary_key=True)
    group_id=db.Column(db.Integer, nullable=False)
    name=db.Column(db.String(200), nullable=False)
    paid=db.Column(db.Integer, default=0)
    expense=db.Column(db.Integer, default=0)
    balance=db.Column(db.Integer, default=0)

    def __repr__(self)->str:
        return f"{self.id} - {self.name}"
    
class Expense(db.Model):
    __bind_key__="expenses"
    id=db.Column(db.Integer, primary_key=True)
    group_id=db.Column(db.Integer, nullable=False)
    name=db.Column(db.String(200), nullable=False)
    amt=db.Column(db.Integer, default=0)
    paid_by=db.Column(db.String, default=0)
    paid_for=db.Column(db.String, default=0)
    date=db.Column(db.String, default=datetime.now().strftime("%d %b %X"))

    def __repr__(self)->str:
        return f"{self.id} - {self.name}"

@app.route('/', methods=['GET', 'POST'])
def create_group():
    if request.method=='POST':
        title=request.form["title"]
        type=request.form["type"]
        date=datetime.now().strftime("%d %b %X")
        group=Group(title=title, type=type, date=date)
        db.session.add(group)
        db.session.commit()
    allGroups=Group.query.all()
    return render_template("index.html", allGroups=allGroups)

@app.route('/change_name/<int:id>', methods=['GET', 'POST'])
def change_name(id):
    if request.method=='POST':
        title=request.form["title"]
        type=request.form["type"]
        group=Group.query.filter_by(id=id).first()
        group.title=title
        group.type=type
        db.session.add(group)
        db.session.commit()
        return redirect("/")
    group=Group.query.filter_by(id=id).first()
    return render_template("update.html", group=group)

@app.route('/delete_group/<int:id>')
def delete_group(id):
    group=Group.query.filter_by(id=id).first()
    db.session.delete(group)
    db.session.commit()
    Member.query.filter_by(group_id=id).delete()
    db.session.commit()
    Expense.query.filter_by(group_id=id).delete()
    db.session.commit()
    return redirect("/")

@app.route('/enter_group/<int:id>', methods=['GET', 'POST'])
def enter_group(id):
    if request.method=='POST':
        title=request.form["title"]
        type=request.form["type"]
        group=Group.query.filter_by(id=id).first()
        group.title=title
        group.type=type
        db.session.add(group)
        db.session.commit()
        return redirect("/")
    group=Group.query.filter_by(id=id).first()
    members=db.session.query(Member).filter_by(group_id=id).all()
    expenses=db.session.query(Expense).filter_by(group_id=id).all()
    return render_template("group.html", group=group, members=members, expenses=expenses)

@app.route('/back_to_index')
def back_to_index():
    allGroups=Group.query.all()
    return render_template("index.html", allGroups=allGroups)

@app.route('/back_to_group/<int:id>')
def back_to_group(id):
    group=Group.query.filter_by(id=id).first()
    members=db.session.query(Member).filter_by(group_id=id).all()
    expenses=db.session.query(Expense).filter_by(group_id=id).all()
    return render_template("group.html", group=group, members=members, expenses=expenses)

@app.route('/add_member/<int:id>', methods=['GET', 'POST'])
def add_member(id):
    if request.method=='POST':
        name=request.form["name"]
        group_id=id
        member=Member(name=name, group_id=group_id)
        db.session.add(member)
        db.session.commit()
        group=Group.query.filter_by(id=id).first()
        members=db.session.query(Member).filter_by(group_id=id).all()
        expenses=db.session.query(Expense).filter_by(group_id=id).all()
        return render_template("group.html", group=group, members=members, expenses=expenses)
    group=Group.query.filter_by(id=id).first()
    return render_template("member.html", group=group)

@app.route('/add_expense/<int:id>', methods=['GET', 'POST'])
def add_expense(id):
    if request.method=='POST':
        name=request.form["name"]
        group_id=id
        amt=int(request.form["amt"])
        paid_by=request.form["paid_by"]
        paid_for=""
        i=0
        for key, val in request.form.items():
            if key.startswith("mem"):
                paid_for+=val
                paid_for+=" "
                i+=1
        if i==0:
            flash('Please add atleast 1 member to split the expense!')
            group=Group.query.filter_by(id=id).first()
            members=db.session.query(Member).filter_by(group_id=id).all()
            return render_template("expense.html", group=group, members=members)
        else:
            mem=Member.query.filter_by(name=paid_by, group_id=group_id).first()
            mem.paid=round(mem.paid+amt, 2)
            mem.balance=round(mem.balance+amt,2)
            db.session.add(mem)
            db.session.commit()
            share=round(amt/i, 2)
            members=db.session.query(Member).filter_by(group_id=id).all()
            for key, val in request.form.items():
                if key.startswith("mem"):
                    for mem in members:
                        if mem.name==val:
                            mem.expense=round(mem.expense+share, 2)
                            mem.balance=round(mem.balance-share, 2)
                            db.session.add(mem)
                            db.session.commit()
            date=datetime.now().strftime("%d %b %X")
            expense=Expense(name=name, group_id=group_id, amt=amt, paid_by=paid_by, paid_for=paid_for, date=date)
            db.session.add(expense)
            db.session.commit()
            group=Group.query.filter_by(id=id).first()
            members=db.session.query(Member).filter_by(group_id=id).all()
            expenses=db.session.query(Expense).filter_by(group_id=id).all()
            return render_template("group.html", group=group, members=members, expenses=expenses)
    group=Group.query.filter_by(id=id).first()
    members=db.session.query(Member).filter_by(group_id=id).all()
    return render_template("expense.html", group=group, members=members)

@app.route('/suggested_payments/<int:id>', methods=['GET', 'POST'])
def suggested_payments(id):
    group=Group.query.filter_by(id=id).first()
    members=db.session.query(Member).filter_by(group_id=id).all()
    payments=[]
    while 1:
        mi=0
        high=0
        ma=0
        low=0
        for mem in members:
            if mem.balance<low:
                low=mem.balance
                mi=mem.id
                mi_name=mem.name
            if mem.balance>high:
                high=mem.balance
                ma=mem.id
                ma_name=mem.name
        if high==0 or low==0:
            break
        if (-low<high):
            message=f"{mi_name} has to pay {-round(low, 2)} to {ma_name}"
            for mem in members:
                if mem.name==mi_name:
                    mem.balance-=low
                if mem.name==ma_name:
                    mem.balance+=low
            payments.append([message, mi, ma, -round(low,2)])
        else:
            message=f"{mi_name} has to pay {round(high,2)} to {ma_name}"
            for mem in members:
                if mem.name==mi_name:
                    mem.balance+=high
                if mem.name==ma_name:
                    mem.balance-=high
            payments.append([message, mi, ma, round(high,2)])
    return render_template("suggested_payments.html", group=group, payments=payments)

@app.route('/change_expense/<int:id>', methods=['GET', 'POST'])
def change_expense(id):
    if request.method=='POST':
        exp=Expense.query.filter_by(id=id).first()
        paid_by_mem=Member.query.filter_by(name=exp.paid_by, group_id=exp.group_id).first()
        paid_by_mem.paid=round(paid_by_mem.paid-exp.amt,2)
        paid_by_mem.balance=round(paid_by_mem.balance-exp.amt,2)
        db.session.add(paid_by_mem)
        db.session.commit()
        paid_for=exp.paid_for.split()
        for by in paid_for:
            share=round(exp.amt/len(paid_for), 2)
            paid_for_mem=Member.query.filter_by(name=by, group_id=exp.group_id).first()
            paid_for_mem.expense=round(paid_for_mem.expense-share, 2)
            paid_for_mem.balance=round(paid_for_mem.balance+share, 2)
            db.session.add(paid_for_mem)
            db.session.commit()
        
        name=request.form["name"]
        group_id=exp.group_id
        amt=int(request.form["amt"])
        paid_by=request.form["paid_by"]
        paid_for=""
        i=0
        for key, val in request.form.items():
            if key.startswith("mem"):
                paid_for+=val
                paid_for+=" "
                i+=1
        if i==0:
            flash('Please add atleast 1 member to split the expense!')
            group=Group.query.filter_by(id=group_id).first()
            members=db.session.query(Member).filter_by(group_id=group_id).all()
            return render_template("expense.html", group=group, members=members)
        else:
            mem=Member.query.filter_by(name=paid_by, group_id=group_id).first()
            mem.paid=round(mem.paid+amt, 2)
            mem.balance=round(mem.balance+amt,2)
            db.session.add(mem)
            db.session.commit()
            share=round(amt/i, 2)
            members=db.session.query(Member).filter_by(group_id=group_id).all()
            for key, val in request.form.items():
                if key.startswith("mem"):
                    for mem in members:
                        if mem.name==val:
                            mem.expense=round(mem.expense+share, 2)
                            mem.balance=round(mem.balance-share, 2)
                            db.session.add(mem)
                            db.session.commit()
            expense=Expense.query.filter_by(id=id).first()
            expense.name=name
            expense.amt=amt
            expense.paid_by=paid_by
            expense.paid_for=paid_for
            db.session.add(expense)
            db.session.commit()
            group=Group.query.filter_by(id=group_id).first()
            members=db.session.query(Member).filter_by(group_id=group_id).all()
            expenses=db.session.query(Expense).filter_by(group_id=group_id).all()
            return render_template("group.html", group=group, members=members, expenses=expenses)
    expense=Expense.query.filter_by(id=id).first()
    group=Group.query.filter_by(id=expense.group_id).first()
    members=db.session.query(Member).filter_by(group_id=expense.group_id).all()
    return render_template("update_expense.html", expense=expense, group=group, members=members)

@app.route('/delete_expense/<int:id>')
def delete_expense(id):
    exp=Expense.query.filter_by(id=id).first()
    paid_by_mem=Member.query.filter_by(name=exp.paid_by, group_id=exp.group_id).first()
    paid_by_mem.paid=round(paid_by_mem.paid-exp.amt,2)
    paid_by_mem.balance=round(paid_by_mem.balance-exp.amt,2)
    db.session.add(paid_by_mem)
    db.session.commit()
    paid_for=exp.paid_for.split()
    for by in paid_for:
        share=round(exp.amt/len(paid_for), 2)
        paid_for_mem=Member.query.filter_by(name=by, group_id=exp.group_id).first()
        paid_for_mem.expense=round(paid_for_mem.expense-share, 2)
        paid_for_mem.balance=round(paid_for_mem.balance+share, 2)
        db.session.add(paid_for_mem)
        db.session.commit()
    exp=Expense.query.filter_by(id=id).first()
    db.session.delete(exp)
    db.session.commit()
    group=Group.query.filter_by(id=exp.group_id).first()
    members=db.session.query(Member).filter_by(group_id=group.id).all()
    expenses=db.session.query(Expense).filter_by(group_id=group.id).all()
    return render_template("group.html", group=group, members=members, expenses=expenses)

@app.route('/save_payments/<payment>')
def save_payments(payment):
    expense=payment.split()
    exp=""+expense[0]+" paid "+expense[4]+" to "+expense[6]
    paid_for=exp[2:len(exp)-2]
    pay=[]
    p = '[\d]+[.\d]+|[\d]*[.][\d]+|[\d]+'
    if re.search(p, payment) is not None:
        for catch in re.finditer(p, payment):
            pay.append(catch[0])
    print(pay)
    member=Member.query.filter_by(id=int(pay[1])).first()
    member.balance=round(member.balance+float(pay[0]), 2)
    member.paid=round(member.paid+float(pay[0]), 2)
    db.session.add(member)
    db.session.commit()
    member=Member.query.filter_by(id=int(pay[2])).first()
    member.balance=round(member.balance-float(pay[0]), 2)
    member.paid=round(member.paid-float(pay[0]), 2)
    db.session.add(member)
    db.session.commit()
    id=member.group_id
    group_id=id
    name="Settled up"
    amt=float(pay[0])
    paid_by=""+expense[0]
    paid_by=paid_by[2:]
    date=datetime.now().strftime("%d %b %X")
    expense=Expense(group_id=group_id, name=name, amt=amt, paid_by=paid_by, paid_for=paid_for, date=date)
    db.session.add(expense)
    db.session.commit()
    group=Group.query.filter_by(id=id).first()
    members=db.session.query(Member).filter_by(group_id=id).all()
    expenses=db.session.query(Expense).filter_by(group_id=id).all()
    return render_template("group.html", group=group, members=members, expenses=expenses)

if __name__=="__main__":
    app.run(debug=True, host='0.0.0.0', port=5005)
