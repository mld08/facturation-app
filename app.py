from flask import Flask, render_template, request, redirect, url_for, flash, make_response, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from decimal import Decimal
from dotenv import load_dotenv
import os
from sqlalchemy import DECIMAL
from collections import Counter, defaultdict
from xhtml2pdf import pisa 
from io import BytesIO
import mimetypes
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


load_dotenv()
app = Flask(__name__)
application=app
app.config['SECRET_KEY'] = 'votre-cle-secrete-ici'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modèle pour les utilisateurs
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' ou 'agent'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

# Modèles de base de données
class Societe(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom_societe = db.Column(db.Text, nullable=False)
    adresse_societe = db.Column(db.Text, nullable=True)
    telephone_societe = db.Column(db.String(20), nullable=True)
    email_societe = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date())
    
    # Relations
    factures = db.relationship('Facture', backref='societe', lazy=True)

class Facture(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_facture = db.Column(db.String(50), unique=True, nullable=False)
    nom_societe = db.Column(db.Text, nullable=False)
    nombre_certificats = db.Column(db.Integer, nullable=False)
    poids = db.Column(db.Text, nullable=True)
    entite = db.Column(db.String(20), nullable=False) 
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)
    prix_total = db.Column(db.Numeric(10, 2), nullable=False)
    date_facture = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date())
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date(), onupdate=datetime.utcnow)
    
    # Clé étrangère
    societe_id = db.Column(db.Integer, db.ForeignKey('societe.id'), nullable=True)

class Certificat(db.Model):
    id_certificat = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_certificat = db.Column(db.Integer, nullable=False)
    nombre_certificats = db.Column(db.Integer, nullable=False)
    poids_certifie_kg = db.Column(db.Text, nullable=True)
    date_facture = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).date())


# Décorateurs pour l'authentification
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Accès refusé. Droits administrateur requis.', 'error')
            return redirect(url_for('liste_factures'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Fonction pour ajouter le contexte utilisateur dans tous les templates
@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())


def image_to_base64(image_path):
    """Convertit une image en base64"""
    try:
        with open(image_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
            
        # Déterminer le type MIME
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = 'image/png'  # Par défaut
            
        return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"Erreur conversion image: {e}")
        return None

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            flash(f'Connexion réussie! Bienvenue {user.username}', 'success')
            
            # Rediriger selon le rôle
            if user.role == 'admin':
                return redirect(url_for('index'))
            else:
                return redirect(url_for('liste_factures'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté avec succès.', 'success')
    return redirect(url_for('login'))

# Routes principales
@app.route('/')
@admin_required
def index():
    factures = Facture.query.order_by(Facture.created_at.desc()).limit(10).all()
    societes = Societe.query.all()
    certificats = Certificat.query.all()
    toutes_les_factures = Facture.query.all()

    # Comptage des entités
    entites = [f.entite for f in toutes_les_factures if f.entite]
    repartition_entites = dict(Counter(entites))  # {'DPSP': 10, 'Aéroport': 5}

    # Montant total par mois
    montant_par_mois = defaultdict(float)
    for f in toutes_les_factures:
        if f.date_facture:
            mois = f.date_facture.strftime('%Y-%m')  # ex : "2025-07"
            montant_par_mois[mois] += float(f.prix_total)  # Assurez-vous que prix_total est un float

    # Trier les mois dans l’ordre chronologique
    mois_tries = sorted(montant_par_mois.keys())
    montants_tries = [montant_par_mois[mois] for mois in mois_tries]

    return render_template('index.html', factures=factures, societes=societes, certificats=certificats, repartition_entites=repartition_entites, mois_tries=mois_tries, montants_tries=montants_tries)

@app.route('/factures')
@login_required
def liste_factures():
    factures = Facture.query.order_by(Facture.created_at.desc()).all()
    return render_template('factures/liste.html', factures=factures)

@app.route('/factures/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_facture():
    if request.method == 'POST':
        # Générer un numéro de facture unique
        derniere_facture = Facture.query.order_by(Facture.numero_facture.desc()).first()
        if derniere_facture:
            dernier_numero = int(derniere_facture.numero_facture.split('-')[1])
            nouveau_numero = f"FACT-{dernier_numero + 1:06d}"
        else:
            nouveau_numero = "FACT-000001"

        # Récupération des données du formulaire
        societe_id = int(request.form['societe_id'])
        nombre_certificats = int(request.form['nombre_certificats'])
        poids = Decimal(request.form['poids'])
        entite = request.form['entite']

        # Récupérer les objets
        societe = Societe.query.get(societe_id)

        # Utilisation d’un prix unitaire fictif (ou à ajouter dans Certificat)
        prix_unitaire = Decimal(request.form['prix_unitaire'])  # Ajuste ou récupère depuis `certificat`

        prix_total = prix_unitaire * poids
        

        # Création de la facture
        facture = Facture(
            numero_facture=str(nouveau_numero),
            nom_societe=societe.nom_societe,
            societe_id=societe_id,
            nombre_certificats=nombre_certificats,
            poids=str(poids),
            entite=entite,
            prix_unitaire=prix_unitaire,
            prix_total=prix_total,
            date_facture=datetime.strptime(request.form['date_facture'], '%Y-%m-%d')
        )

        db.session.add(facture)
        db.session.commit()

        flash('Facture créée avec succès!', 'success')
        return redirect(url_for('voir_facture', id=facture.id))

    societes = Societe.query.all()
    return render_template('factures/nouveau.html', societes=societes, datetime=datetime)

@app.route('/factures/<int:id>')
@login_required
def voir_facture(id):
    facture = Facture.query.get_or_404(id)
    return render_template('factures/voir.html', facture=facture)

@app.route('/factures/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_facture(id):
    facture = Facture.query.get_or_404(id)

    if request.method == 'POST':
        societe_id = int(request.form['societe_id'])
        nombre_certificats = int(request.form['nombre_certificats'])
        poids = Decimal(request.form['poids'])
        prix_unitaire = Decimal(request.form['prix_unitaire'])

        # Récupération de la société
        societe = Societe.query.get(societe_id)

        # Recalcul du prix total
        prix_total = prix_unitaire * poids

        # Mise à jour de la facture
        facture.nom_societe = societe.nom_societe
        facture.societe_id = societe_id
        facture.nombre_certificats = nombre_certificats
        facture.poids = str(poids)
        facture.prix_unitaire = prix_unitaire
        facture.prix_total = prix_total
        facture.entite = request.form['entite']
        facture.date_facture = datetime.strptime(request.form['date_facture'], '%Y-%m-%d')
        facture.updated_at = datetime.utcnow()

        db.session.commit()

        flash('Facture modifiée avec succès!', 'success')
        return redirect(url_for('voir_facture', id=facture.id))

    societes = Societe.query.all()
    return render_template('factures/modifier.html', facture=facture, societes=societes, datetime=datetime)

@app.route('/factures/<int:id>/supprimer', methods=['POST'])
@admin_required 
def supprimer_facture(id):
    facture = Facture.query.get_or_404(id)
    db.session.delete(facture)
    db.session.commit()
    flash('Facture supprimée avec succès!', 'success')
    return redirect(url_for('liste_factures'))


@app.route('/factures/<int:id>/pdf')
@login_required
def generer_pdf(id):
    facture = Facture.query.get_or_404(id)

    logo_path = os.path.join(app.static_folder, 'img', 'dpsp.png')
    signature_path = os.path.join(app.static_folder, 'img', 'senegal.jpg')
    # Convertir les images en base64
    logo_base64 = image_to_base64(logo_path) if os.path.exists(logo_path) else None
    signature_base64 = image_to_base64(signature_path) if os.path.exists(signature_path) else None

    
    
    # Rendu du template HTML
    html = render_template('factures/pdf.html', facture=facture, logo_base64=logo_base64,
                         signature_base64=signature_base64)
    
    # Créer un buffer
    result = BytesIO()
    
    # Convertir HTML en PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        # Récupérer le PDF
        pdf_data = result.getvalue()
        result.close()
        
        # Créer la réponse
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=facture_{facture.numero_facture}.pdf'
        
        return response
    
    return "Erreur lors de la génération du PDF", 500

# Routes pour la gestion des sociétés
@app.route('/societes')
@login_required
def liste_societes():
    societes = Societe.query.all()
    return render_template('societes/liste.html', societes=societes)

@app.route('/societes/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_societe():
    if request.method == 'POST':
        societe = Societe(
            nom_societe=request.form['nom_societe'],
            adresse_societe=request.form['adresse_societe'],
            telephone_societe=request.form['telephone_societe'],
            email_societe=request.form['email_societe']
        )
        db.session.add(societe)
        db.session.commit()
        flash('Société ajoutée avec succès!', 'success')
        return redirect(url_for('liste_societes'))
    
    return render_template('societes/nouvelle.html')

@app.route('/societes/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_societe(id):
    societe = Societe.query.get_or_404(id)

    if request.method == 'POST':
        societe.nom_societe = request.form['nom_societe']
        societe.adresse_societe = request.form['adresse_societe']
        societe.telephone_societe = request.form['telephone_societe']
        societe.email_societe = request.form['email_societe']
        db.session.commit()
        flash('Société modifiée avec succès!', 'success')
        return redirect(url_for('liste_societes'))

    return render_template('societes/modifier.html', societe=societe)

@app.route('/societes/<int:id>/supprimer', methods=['POST'])
@admin_required
def supprimer_societe(id):
    societe = Societe.query.get_or_404(id)
    db.session.delete(societe)
    db.session.commit()
    flash('Société supprimée avec succès!', 'success')
    return redirect(url_for('liste_societes'))


# Routes pour la gestion des certificats
@app.route('/certificats')
@login_required
def liste_certificats():
    certificats = Certificat.query.all()
    return render_template('certificats/liste.html', certificats=certificats)

@app.route('/certificats/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_certificat():
    if request.method == 'POST':
        certificat = Certificat(
            numero_certificat=request.form['numero_certificat'],
            nombre_certificats=Decimal(request.form['nombre_certificats']),
            poids_certifie_kg=Decimal(request.form['poids_certifie_kg']),
            date_facture=datetime.strptime(request.form['date_facture'], '%Y-%m-%d')
        )
        db.session.add(certificat)
        db.session.commit()
        flash('Certificat ajouté avec succès!', 'success')
        return redirect(url_for('liste_certificats'))
    
    return render_template('certificats/nouveau.html')

@app.route('/certificats/<int:id_certificat>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_certificat(id_certificat):
    certificat = Certificat.query.get_or_404(id_certificat)

    if request.method == 'POST':
        certificat.numero_certificat = request.form['numero_certificat']
        certificat.nombre_certificats = Decimal(request.form['nombre_certificats'])
        certificat.poids_certifie_kg = Decimal(request.form['poids_certifie_kg'])
        certificat.date_facture = datetime.strptime(request.form['date_facture'], '%Y-%m-%d')
        db.session.commit()
        flash('Certificat modifié avec succès!', 'success')
        return redirect(url_for('liste_certificats'))

    return render_template('certificats/modifier.html', certificat=certificat)

@app.route('/certificats/<int:id_certificat>/supprimer', methods=['POST'])
@admin_required
def supprimer_certificat(id_certificat):
    certificat = Certificat.query.get_or_404(id_certificat)
    db.session.delete(certificat)
    db.session.commit()
    flash('Certificat supprimé avec succès!', 'success')
    return redirect(url_for('liste_certificats'))

# Fonction pour initialiser la base de données
def init_db():
    with app.app_context():
        db.create_all()

        # Créer les utilisateurs par défaut s'ils n'existent pas
        if not User.query.first():
            # 4 comptes admin
            admin1 = User(username='admin', role='admin')
            admin1.set_password('Adp1fidx$')
            
            admin2 = User(username='directeur', role='admin')
            admin2.set_password('dir@25')
            
            admin3 = User(username='bureaucertification', role='admin')
            admin3.set_password('bcertif@25')

            admin4 = User(username='sis', role='admin')
            admin4.set_password('sis@25')
            
            # 2 comptes agent
            agent1 = User(username='agentdpsp', role='agent')
            agent1.set_password('agentdpsp@25')
            
            agent2 = User(username='agentaeroport', role='agent')
            agent2.set_password('agentaeroport@25')
            
            db.session.add_all([admin1, admin2, admin3, admin4, agent1, agent2])
            db.session.commit()
            
            print("Utilisateurs créés avec succés!")
        
        # Ajouter quelques données de test si aucune donnée n'existe
        # if not Societe.query.first():
        #     societe_test = Societe(
        #         nom_societe="Société Test SARL",
        #         adresse_societe="123 Rue de la Paix, Dakar",
        #         telephone_societe="77 123 45 67",
        #         email_societe="contact@societetest.sn"
        #     )
            
        #     db.session.add(societe_test)
        #     db.session.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)