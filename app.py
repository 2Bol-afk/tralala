from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import json
from datetime import datetime
import io

app = Flask(__name__)
DATABASE = 'students.db'

# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade INTEGER NOT NULL,
            section TEXT NOT NULL,
            contact TEXT NOT NULL,
            date_registered TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Helper function to get db connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# 1. Add Student (POST)
@app.route('/student', methods=['POST'])
def add_student():
    data = request.get_json()
    
    if not all(k in data for k in ('name', 'grade', 'section', 'contact')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    date_registered = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO students (name, grade, section, contact, date_registered)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['name'], data['grade'], data['section'], data['contact'], date_registered))
    conn.commit()
    student_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        'message': 'Student added successfully',
        'id': student_id
    }), 201

# 2. View All Students (GET)
@app.route('/students', methods=['GET'])
def get_all_students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students ORDER BY id DESC')
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(students)

# 3. View Single Student (GET)
@app.route('/student/<int:id>', methods=['GET'])
def get_student(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
    student = cursor.fetchone()
    conn.close()
    
    if student:
        return jsonify(dict(student))
    return jsonify({'error': 'Student not found'}), 404

# 4. Update Student (PUT)
@app.route('/student/<int:id>', methods=['PUT'])
def update_student(id):
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE id = ?', (id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    
    name = data.get('name', student['name'])
    grade = data.get('grade', student['grade'])
    section = data.get('section', student['section'])
    contact = data.get('contact', student['contact'])
    
    cursor.execute('''
        UPDATE students 
        SET name = ?, grade = ?, section = ?, contact = ?
        WHERE id = ?
    ''', (name, grade, section, contact, id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Student updated successfully'})

# 5. Delete Student (DELETE)
@app.route('/student/<int:id>', methods=['DELETE'])
def delete_student(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    if rows_affected > 0:
        return jsonify({'message': 'Student deleted successfully'})
    return jsonify({'error': 'Student not found'}), 404

# 6. Search Student (GET)
@app.route('/students/search', methods=['GET'])
def search_students():
    name = request.args.get('name', '')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM students 
        WHERE LOWER(name) LIKE LOWER(?)
        ORDER BY name
    ''', (f'%{name}%',))
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(students)

# 7. Count Students (GET)
@app.route('/students/count', methods=['GET'])
def count_students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM students')
    count = cursor.fetchone()['count']
    conn.close()
    
    return jsonify({'count': count})

# 8. Export Students (GET)
@app.route('/students/export', methods=['GET'])
def export_students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students')
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Create JSON file in memory
    json_data = json.dumps(students, indent=2)
    buffer = io.BytesIO(json_data.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/json',
        as_attachment=True,
        download_name=f'students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )

# 9. Import Students (POST)
@app.route('/students/import', methods=['POST'])
def import_students():
    data = request.get_json()
    
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a JSON array'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    imported = 0
    
    for student in data:
        if all(k in student for k in ('name', 'grade', 'section', 'contact')):
            date_registered = student.get('date_registered', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            cursor.execute('''
                INSERT INTO students (name, grade, section, contact, date_registered)
                VALUES (?, ?, ?, ?, ?)
            ''', (student['name'], student['grade'], student['section'], student['contact'], date_registered))
            imported += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Students imported successfully',
        'imported': imported
    })

# Frontend HTML
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; background: #f8f9fa; }
        .card { box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn-action { margin: 2px; }
        .student-count { font-size: 1.2rem; font-weight: bold; color: #0d6efd; }
        @media (max-width: 768px) {
            .table-responsive { font-size: 0.9rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row mb-4">
            <div class="col">
                <h1 class="text-center"><i class="bi bi-mortarboard-fill"></i> Student Manager</h1>
            </div>
        </div>

        <!-- Stats Card -->
        <div class="row mb-3">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-body text-center">
                        <span class="student-count">Total Students: <span id="studentCount">0</span></span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Add Student Form -->
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0"><i class="bi bi-person-plus"></i> Add Student</h5>
                    </div>
                    <div class="card-body">
                        <form id="addStudentForm">
                            <div class="mb-3">
                                <label class="form-label">Name</label>
                                <input type="text" class="form-control" id="name" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Grade</label>
                                <input type="number" class="form-control" id="grade" min="1" max="12" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Section</label>
                                <input type="text" class="form-control" id="section" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Contact</label>
                                <input type="text" class="form-control" id="contact" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                <i class="bi bi-plus-circle"></i> Add Student
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Students List -->
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0"><i class="bi bi-list-ul"></i> Students List</h5>
                    </div>
                    <div class="card-body">
                        <!-- Search Bar -->
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <input type="text" class="form-control" id="searchInput" placeholder="Search by name...">
                            </div>
                            <div class="col-md-6 text-end">
                                <button class="btn btn-info btn-sm" onclick="exportStudents()">
                                    <i class="bi bi-download"></i> Export
                                </button>
                                
                            </div>
                        </div>

                        <!-- Table -->
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>ID</th>
                                        <th>Name</th>
                                        <th>Year</th>
                                        <th>Section</th>
                                        <th>Contact</th>
                                        <th>Registered</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="studentsTable">
                                    <tr>
                                        <td colspan="7" class="text-center">Loading...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Edit Modal -->
    <div class="modal fade" id="editModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Edit Student</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="editStudentForm">
                        <input type="hidden" id="editId">
                        <div class="mb-3">
                            <label class="form-label">Name</label>
                            <input type="text" class="form-control" id="editName" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Year</label>
                            <input type="number" class="form-control" id="editGrade" min="1" max="12" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Section</label>
                            <input type="text" class="form-control" id="editSection" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Contact</label>
                            <input type="text" class="form-control" id="editContact" required>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="updateStudent()">Save Changes</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let editModal;

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            editModal = new bootstrap.Modal(document.getElementById('editModal'));
            loadStudents();
            updateCount();

            // Add student form submit
            document.getElementById('addStudentForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                await addStudent();
            });

            // Search functionality
            document.getElementById('searchInput').addEventListener('input', (e) => {
                if (e.target.value) {
                    searchStudents(e.target.value);
                } else {
                    loadStudents();
                }
            });
        });

        // Load all students
        async function loadStudents() {
            try {
                const response = await fetch('/students');
                const students = await response.json();
                displayStudents(students);
                updateCount();
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error loading students', 'danger');
            }
        }

        // Display students in table
        function displayStudents(students) {
            const tbody = document.getElementById('studentsTable');
            if (students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No students found</td></tr>';
                return;
            }

            tbody.innerHTML = students.map(s => `
                <tr>
                    <td>${s.id}</td>
                    <td>${s.name}</td>
                    <td>${s.grade}</td>
                    <td>${s.section}</td>
                    <td>${s.contact}</td>
                    <td>${new Date(s.date_registered).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-warning btn-action" onclick="openEditModal(${s.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-danger btn-action" onclick="deleteStudent(${s.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }

        // Add student
        async function addStudent() {
            const data = {
                name: document.getElementById('name').value,
                grade: parseInt(document.getElementById('grade').value),
                section: document.getElementById('section').value,
                contact: document.getElementById('contact').value
            };

            try {
                const response = await fetch('/student', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    showAlert('Student added successfully!', 'success');
                    document.getElementById('addStudentForm').reset();
                    loadStudents();
                } else {
                    showAlert('Error adding student', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error adding student', 'danger');
            }
        }

        // Open edit modal
        async function openEditModal(id) {
            try {
                const response = await fetch(`/student/${id}`);
                const student = await response.json();

                document.getElementById('editId').value = student.id;
                document.getElementById('editName').value = student.name;
                document.getElementById('editGrade').value = student.grade;
                document.getElementById('editSection').value = student.section;
                document.getElementById('editContact').value = student.contact;

                editModal.show();
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error loading student data', 'danger');
            }
        }

        // Update student
        async function updateStudent() {
            const id = document.getElementById('editId').value;
            const data = {
                name: document.getElementById('editName').value,
                grade: parseInt(document.getElementById('editGrade').value),
                section: document.getElementById('editSection').value,
                contact: document.getElementById('editContact').value
            };

            try {
                const response = await fetch(`/student/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    showAlert('Student updated successfully!', 'success');
                    editModal.hide();
                    loadStudents();
                } else {
                    showAlert('Error updating student', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error updating student', 'danger');
            }
        }

        // Delete student
        async function deleteStudent(id) {
            if (!confirm('Are you sure you want to delete this student?')) return;

            try {
                const response = await fetch(`/student/${id}`, { method: 'DELETE' });
                
                if (response.ok) {
                    showAlert('Student deleted successfully!', 'success');
                    loadStudents();
                } else {
                    showAlert('Error deleting student', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error deleting student', 'danger');
            }
        }

        // Search students
        async function searchStudents(name) {
            try {
                const response = await fetch(`/students/search?name=${encodeURIComponent(name)}`);
                const students = await response.json();
                displayStudents(students);
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error searching students', 'danger');
            }
        }

        // Update count
        async function updateCount() {
            try {
                const response = await fetch('/students/count');
                const data = await response.json();
                document.getElementById('studentCount').textContent = data.count;
            } catch (error) {
                console.error('Error:', error);
            }
        }

        // Export students
        function exportStudents() {
            window.location.href = '/students/export';
            showAlert('Students exported successfully!', 'success');
        }

        
        // Show alert
        function showAlert(message, type) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
            alertDiv.style.zIndex = '9999';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(alertDiv);
            setTimeout(() => alertDiv.remove(), 3000);
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)