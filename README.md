# Fixltpro - IT Support Ticketing System

Fixltpro is a comprehensive IT support ticketing platform designed for Arabic-speaking organizations. This web-based system helps manage and track computer-related issues through an organized workflow.

![Fixltpro](https://via.placeholder.com/800x400?text=Fixltpro+IT+Support+Ticketing+System)

## Features

- **Ticket Management**: Create, assign, track, and resolve support tickets
- **Role-Based Access Control**: Admin, maintenance staff, and employee user roles
- **Priority Levels**: Configurable response times based on ticket priority
- **Categorization**: Organize tickets by categories (Hardware, Network, Software, etc.)
- **Arabic Interface**: Fully localized for Arabic users with RTL support
- **Dashboard & Analytics**: Track performance metrics and visualize data
- **Activity Logging**: Monitor all actions in the system
- **Responsive Design**: Works on all device sizes

## Tech Stack

- **Backend**: Python 3.x with Flask framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **ORM**: SQLAlchemy
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5 with RTL support
- **Authentication**: Flask-Login with secure password hashing
- **Form Handling**: Flask-WTF with CSRF protection

## Quick Start

### Prerequisites

- Python 3.7 or newer
- Git (optional, for cloning the repository)

### Installation

1. Clone the repository or download the source code:
   ```
   git clone https://github.com/yourusername/fixltpro.git
   cd fixltpro
   ```

2. Run the setup script to create the virtual environment and install dependencies:
   ```
   setup.bat
   ```
   
3. After setup completes, run the application:
   ```
   run.bat
   ```

4. Access the application:
   - The run script will automatically open your browser to the application
   - For first-time use, navigate to `/setup` to initialize the database
   - Use the default admin credentials to log in:
     - Username: `admin`
     - Password: `admin123`

## Project Structure

```
fixltpro/
├── app.py                      # Main application file
├── setup.bat                   # Setup script
├── run.bat                     # Run script
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── fixltpro.db                 # SQLite database
├── static/                     # Static assets
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript files
│   └── img/                    # Images
└── templates/                  # HTML templates
    ├── admin_dashboard.html
    ├── create_ticket.html
    ├── login.html
    ├── maintenance_dashboard.html
    ├── profile.html
    └── ...
```

## Usage

### User Roles

1. **Admin**:
   - Manage users, categories, and priorities
   - View all tickets and reports
   - Assign tickets to maintenance staff
   - Access analytics and system settings

2. **Maintenance Staff**:
   - View assigned tickets
   - Update ticket status
   - Add comments to tickets
   - View personal performance metrics

3. **Employees**:
   - Create new support tickets
   - View status of submitted tickets
   - Add comments to tickets
   - Update personal profile

### Ticket Workflow

1. Employee creates a ticket with category and priority
2. System calculates due date based on priority
3. Admin assigns ticket to maintenance staff
4. Maintenance staff updates ticket status
5. All parties can add comments for clarification
6. Ticket is marked as completed when resolved

## Customization

### Changing Database

The system uses SQLite by default. To use PostgreSQL:

1. Update the database URI in `app.py`:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/fixltpro'
   ```

2. Install PostgreSQL driver:
   ```
   pip install psycopg2-binary
   ```

### Modifying Categories and Priorities

After initial setup, log in as admin to add, edit, or remove:
- Ticket categories
- Priority levels
- Response time thresholds

## Development

### Setting Up Development Environment

1. Follow the installation steps above
2. Make code changes as needed
3. Restart the application to see changes

### Code Guidelines

- Keep code and variable names in English
- Keep user-facing content in Arabic
- Follow PEP 8 style guidelines for Python code
- Use meaningful variable and function names
- Add comments for complex logic

## Deployment

### Production Recommendations

1. Use a production WSGI server (Gunicorn is included in requirements):
   ```
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```

2. Set up a reverse proxy (Nginx or Apache)

3. Use PostgreSQL instead of SQLite

4. Set proper environment variables:
   ```
   FLASK_ENV=production
   SECRET_KEY=your_secure_secret_key
   ```

5. Implement regular database backups

## Security Considerations

- Passwords are hashed using Werkzeug's security functions
- CSRF protection is implemented for all forms
- Session management includes timeouts
- Role-based access control prevents unauthorized actions
- Input validation is applied to all user inputs

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Bootstrap 5 for the responsive UI framework
- Flask and its extensions for the backend framework
- Chart.js for data visualization components

---

For issues, feature requests, or contributions, please create an issue or pull request on GitHub.
