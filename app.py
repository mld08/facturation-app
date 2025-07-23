# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import pdfkit
from decimal import Decimal
from dotenv import load_dotenv
import os
from sqlalchemy import DECIMAL


load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre-cle-secrete-ici'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modèles de base de données
class Societe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    adresse = db.Column(db.Text)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date())
    
    # Relation avec les factures
    factures = db.relationship('Facture', backref='societe', lazy=True)

class Certificat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prix_unitaire = db.Column(DECIMAL(10, 2), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date())
    
    # Relation avec les lignes de facture
    lignes_facture = db.relationship('LigneFacture', backref='certificat', lazy=True)

class Facture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_facture = db.Column(db.String(50), unique=True, nullable=False)
    date_facture = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    societe_id = db.Column(db.Integer, db.ForeignKey('societe.id'), nullable=False)
    montant_total = db.Column(DECIMAL(10, 2), nullable=False, default=0)
    statut = db.Column(db.String(20), default='En attente')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date())
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date(), onupdate=datetime.utcnow)
    
    # Relation avec les lignes de facture
    lignes = db.relationship('LigneFacture', backref='facture', lazy=True, cascade='all, delete-orphan')

class LigneFacture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    facture_id = db.Column(db.Integer, db.ForeignKey('facture.id'), nullable=False)
    certificat_id = db.Column(db.Integer, db.ForeignKey('certificat.id'), nullable=False)
    nombre_certificats = db.Column(db.Integer, nullable=False)
    poids = db.Column(DECIMAL(10, 2), nullable=False)
    prix_unitaire = db.Column(DECIMAL(10, 2), nullable=False)
    montant = db.Column(DECIMAL(10, 2), nullable=False)

# from datetime import datetime
# from flask_sqlalchemy import SQLAlchemy

# db = SQLAlchemy()

# class Societe(db.Model):
#     id = db.Column(db.Integer, primary_key=True)  # ID automatique
#     nom = db.Column(db.String(200), nullable=False)  # Nom de la Société
#     adresse = db.Column(db.Text)  # Adresse Société
#     telephone = db.Column(db.String(20))  # Téléphone Société
#     email = db.Column(db.String(100))  # E-Mail Société
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     # Relation avec les factures
#     factures = db.relationship('Facture', backref='societe', lazy=True)


# class Certificat(db.Model):
#     id = db.Column(db.Integer, primary_key=True)  # ID Certificat (automatique)
#     numero_certificat = db.Column(db.String(100), nullable=True)  # Numéro Certificat
#     nombre_certificats = db.Column(db.Integer, nullable=True)  # Nombre de certificats
#     poids_kg = db.Column(db.String(100))  # Poids Certifié en Kg
#     date_facture = db.Column(db.DateTime, nullable=True)  # Date Facture
#     prix_unitaire = db.Column(db.Numeric(10, 2), nullable=True)  # Ajouté pour la logique métier
#     description = db.Column(db.Text)

#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     # Relation avec les lignes de facture
#     lignes_facture = db.relationship('LigneFacture', backref='certificat', lazy=True)


# class Facture(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     numero_facture = db.Column(db.String(50), unique=True, nullable=False)  # Numéro facture
#     societe_id = db.Column(db.Integer, db.ForeignKey('societe.id'), nullable=False)  # Nom Société (clé étrangère)
#     nombre_certificats = db.Column(db.Integer, nullable=True)
#     poids_total = db.Column(db.String(100), nullable=True)  # Poids
#     montant = db.Column(db.Numeric(10, 2), nullable=True)  # Montant (CFA)
#     prix_total = db.Column(db.Numeric(10, 2), nullable=True)  # Prix Total (CFA)
#     date_facture = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

#     statut = db.Column(db.String(20), default='En attente')
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     # Relation avec les lignes de facture
#     lignes = db.relationship('LigneFacture', backref='facture', lazy=True, cascade='all, delete-orphan')


# class LigneFacture(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     facture_id = db.Column(db.Integer, db.ForeignKey('facture.id'), nullable=False)
#     certificat_id = db.Column(db.Integer, db.ForeignKey('certificat.id'), nullable=False)
    
#     prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)
#     montant = db.Column(db.Numeric(10, 2), nullable=False)


# Routes principales
@app.route('/')
def index():
    factures = Facture.query.order_by(Facture.created_at.desc()).limit(10).all()
    return render_template('index.html', factures=factures)

@app.route('/factures')
def liste_factures():
    factures = Facture.query.order_by(Facture.created_at.desc()).all()
    return render_template('factures/liste.html', factures=factures)

@app.route('/factures/nouvelle', methods=['GET', 'POST'])
def nouvelle_facture():
    if request.method == 'POST':
        # Générer un numéro de facture unique
        derniere_facture = Facture.query.order_by(Facture.id.desc()).first()
        if derniere_facture:
            dernier_numero = int(derniere_facture.numero_facture.split('-')[1])
            nouveau_numero = f"FACT-{dernier_numero + 1:06d}"
        else:
            nouveau_numero = "FACT-000001"
        
        # Créer la facture
        facture = Facture(
            numero_facture=nouveau_numero,
            date_facture=datetime.strptime(request.form['date_facture'], '%Y-%m-%d').date(),
            societe_id=request.form['societe_id']
        )
        
        db.session.add(facture)
        db.session.flush()  # Pour obtenir l'ID de la facture
        
        # Ajouter les lignes de facture
        certificats_ids = request.form.getlist('certificat_id[]')
        nombres = request.form.getlist('nombre_certificats[]')
        poids_list = request.form.getlist('poids[]')
        
        montant_total = Decimal('0')
        
        for i in range(len(certificats_ids)):
            if certificats_ids[i] and nombres[i] and poids_list[i]:
                certificat = Certificat.query.get(certificats_ids[i])
                nombre = int(nombres[i])
                poids = Decimal(poids_list[i])
                montant_ligne = certificat.prix_unitaire * nombre * poids
                
                ligne = LigneFacture(
                    facture_id=facture.id,
                    certificat_id=certificats_ids[i],
                    nombre_certificats=nombre,
                    poids=poids,
                    prix_unitaire=certificat.prix_unitaire,
                    montant=montant_ligne
                )
                db.session.add(ligne)
                montant_total += montant_ligne
        
        facture.montant_total = montant_total
        db.session.commit()
        
        flash('Facture créée avec succès!', 'success')
        return redirect(url_for('voir_facture', id=facture.id))
    
    societes = Societe.query.all()
    certificats = Certificat.query.all()
    return render_template('factures/nouvelle.html', societes=societes, certificats=certificats, datetime=datetime)

@app.route('/factures/<int:id>')
def voir_facture(id):
    facture = Facture.query.get_or_404(id)
    return render_template('factures/voir.html', facture=facture)

@app.route('/factures/<int:id>/modifier', methods=['GET', 'POST'])
def modifier_facture(id):
    facture = Facture.query.get_or_404(id)
    
    if request.method == 'POST':
        facture.date_facture = datetime.strptime(request.form['date_facture'], '%Y-%m-%d').date()
        facture.societe_id = request.form['societe_id']
        
        # Supprimer les anciennes lignes
        LigneFacture.query.filter_by(facture_id=facture.id).delete()
        
        # Ajouter les nouvelles lignes
        certificats_ids = request.form.getlist('certificat_id[]')
        nombres = request.form.getlist('nombre_certificats[]')
        poids_list = request.form.getlist('poids[]')
        
        montant_total = Decimal('0')
        
        for i in range(len(certificats_ids)):
            if certificats_ids[i] and nombres[i] and poids_list[i]:
                certificat = Certificat.query.get(certificats_ids[i])
                nombre = int(nombres[i])
                poids = Decimal(poids_list[i])
                montant_ligne = certificat.prix_unitaire * nombre * poids
                
                ligne = LigneFacture(
                    facture_id=facture.id,
                    certificat_id=certificats_ids[i],
                    nombre_certificats=nombre,
                    poids=poids,
                    prix_unitaire=certificat.prix_unitaire,
                    montant=montant_ligne
                )
                db.session.add(ligne)
                montant_total += montant_ligne
        
        facture.montant_total = montant_total
        facture.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Facture modifiée avec succès!', 'success')
        return redirect(url_for('voir_facture', id=facture.id))
    
    societes = Societe.query.all()
    certificats = Certificat.query.all()
    return render_template('factures/modifier.html', facture=facture, societes=societes, certificats=certificats)

@app.route('/factures/<int:id>/pdf')
def generer_pdf(id):
    facture = Facture.query.get_or_404(id)
    html = render_template('factures/pdf.html', facture=facture)
    
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None
    }
    
    pdf = pdfkit.from_string(html, False, options=options)
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=facture_{facture.numero_facture}.pdf'
    
    return response

# Routes pour la gestion des sociétés
@app.route('/societes')
def liste_societes():
    societes = Societe.query.all()
    return render_template('societes/liste.html', societes=societes)

@app.route('/societes/nouvelle', methods=['GET', 'POST'])
def nouvelle_societe():
    if request.method == 'POST':
        societe = Societe(
            nom=request.form['nom'],
            adresse=request.form['adresse'],
            telephone=request.form['telephone'],
            email=request.form['email']
        )
        db.session.add(societe)
        db.session.commit()
        flash('Société ajoutée avec succès!', 'success')
        return redirect(url_for('liste_societes'))
    
    return render_template('societes/nouvelle.html')

# Routes pour la gestion des certificats
@app.route('/certificats')
def liste_certificats():
    certificats = Certificat.query.all()
    return render_template('certificats/liste.html', certificats=certificats)

@app.route('/certificats/nouveau', methods=['GET', 'POST'])
def nouveau_certificat():
    if request.method == 'POST':
        certificat = Certificat(
            nom=request.form['nom'],
            prix_unitaire=Decimal(request.form['prix_unitaire']),
            description=request.form['description']
        )
        db.session.add(certificat)
        db.session.commit()
        flash('Certificat ajouté avec succès!', 'success')
        return redirect(url_for('liste_certificats'))
    
    return render_template('certificats/nouveau.html')

# Fonction pour initialiser la base de données
def init_db():
    with app.app_context():
        db.create_all()
        
        # Ajouter quelques données de test si aucune donnée n'existe
        if not Societe.query.first():
            societe_test = Societe(
                nom="Société Test SARL",
                adresse="123 Rue de la Paix, Dakar",
                telephone="77 123 45 67",
                email="contact@societetest.sn"
            )
            
            certificat_test = Certificat(
                nom="Certificat Qualité",
                prix_unitaire=Decimal('5000.00'),
                description="Certificat de qualité standard"
            )
            
            db.session.add(societe_test)
            db.session.add(certificat_test)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)