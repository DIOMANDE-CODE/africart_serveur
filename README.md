# Contacts, licence et contributeurs

**Contact** :
- Email : [pyth.os201@gmail.com]

**Licence** :
Ce projet est sous licence MIT.

**Contributeurs** :
- [DIOMANDE DROH MARTIAL]

---
# Modules et API

Le projet expose plusieurs endpoints via Django REST Framework :

- **authentification/** : Inscription, connexion, gestion des droits.
- **clients/** : CRUD clients, gestion profils.
- **produits/** : CRUD produits, gestion catégories, alertes stock.
- **commandes/** : Création et gestion des commandes.
- **ventes/** : Gestion des ventes.
- **statistiques/** : Accès aux statistiques.
- **utilisateurs/** : Gestion avancée des utilisateurs.

---
# Lancement et tests

1. **Lancer le serveur Django** :
	```bash
	python manage.py runserver
	```

2. **Exécuter les tests unitaires** :
	```bash
	python manage.py test
	```

---
# Structure du projet

```
africart_serveur/
├── africart_serveur/        # Configuration Django
├── authentification/        # Gestion des utilisateurs/admin
├── clients/                 # Gestion des clients
├── commandes/               # Gestion des commandes
├── produits/                # Gestion des produits
├── utilisateurs/            # Modèle utilisateur custom
├── ventes/                  # Gestion des ventes
├── statistiques/            # Statistiques et reporting
├── utils/                   # Utilitaires (JWT, etc.)
├── media/                   # Fichiers médias
├── staticfiles/             # Fichiers statiques
├── requirements.txt         # Dépendances Python
├── variable.env             # Variables d'environnement
├── db.sqlite3               # Base de données SQLite
├── manage.py                # Commandes Django
```

---
# Installation et configuration

1. **Cloner le projet** :
	```bash
	git clone <url-du-repo>
	```

2. **Créer et activer l'environnement virtuel** :
	```bash
	python -m venv africa_serveur_env
	africa_serveur_env\Scripts\activate
	```

3. **Installer les dépendances** :
	```bash
	pip install -r requirements.txt
	```

4. **Configurer les variables d'environnement** :
	Remplir le fichier `variable.env` avec vos clés Cloudinary et les paramètres CORS.

5. **Configurer la base de données** :
	Par défaut, le projet utilise SQLite. Pour utiliser une autre base, modifier `settings.py`.

---

# AfriCart

AfriCart est une plateforme e-commerce dédiée à la vente et l'achat de produits africains. Ce projet vise à faciliter la mise en relation entre vendeurs et acheteurs, tout en offrant une gestion complète des produits, commandes, clients et statistiques.

Le backend est développé avec Django et Django REST Framework, permettant une API robuste et sécurisée pour la gestion des différentes ressources.

---
