// Datos de ejemplo (simulación de base de datos local)
let operators = [
    {
        id: 1,
        name: "Juan Pérez García",
        number: "OP-001",
        bloodType: "O+",
        rfc: "PEGJ850315XY9",
        description: "Operador con 5 años de experiencia en el área de logística. Especializado en transporte de materiales y gestión de rutas."
    },
    {
        id: 2,
        name: "María González López",
        number: "OP-002",
        bloodType: "A+",
        rfc: "GOLM901225AB3",
        description: "Operadora certificada en manejo de equipo pesado. Responsable y comprometida con la seguridad operacional."
    },
    {
        id: 3,
        name: "Carlos Rodríguez Martínez",
        number: "OP-003",
        bloodType: "B-",
        rfc: "ROMC880720CD5",
        description: "Operador senior con certificaciones en seguridad industrial. Instructor de nuevos operadores."
    }
];

let machines = [
    {
        id: 1,
        name: "Torno convencional",
        description: "Máquina herramienta que permite mecanizar piezas de forma geométrica de revolución. Utiliza herramientas de corte para dar forma a materiales como metal, madera o plástico mediante rotación. Ideal para trabajos de precisión y fabricación de ejes, poleas y piezas cilíndricas.",
        manualLink: "https://ejemplo.com/manual-torno.pdf"
    },
    {
        id: 2,
        name: "Fresadora convencional",
        description: "Máquina que realiza trabajos de mecanizado por arranque de viruta mediante el movimiento de una herramienta rotativa de varios filos de corte. Perfecta para crear ranuras, chaflanes, engranajes y superficies planas o curvas con alta precisión.",
        manualLink: "https://ejemplo.com/manual-fresadora.pdf"
    },
    {
        id: 3,
        name: "ROMI 1250 - A",
        description: "Torno CNC de alta precisión con control numérico computarizado. Capacidad para trabajar piezas de hasta 1250mm de longitud. Sistema automatizado que permite programación avanzada, repetibilidad perfecta y producción en serie con excelente acabado superficial.",
        manualLink: "https://ejemplo.com/manual-romi-1250.pdf"
    }
];

let reports = [
    {
        id: 1,
        machineId: 1,
        title: "Producción Mensual - Octubre 2024",
        imageData: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect width='400' height='300' fill='%23f0f0f0'/%3E%3Ctext x='200' y='150' font-family='Arial' font-size='16' text-anchor='middle' fill='%23666'%3EGráfica de Ejemplo%3C/text%3E%3C/svg%3E",
        description: "Este reporte muestra un incremento del 15% en la producción comparado con el mes anterior. Los principales factores incluyen la optimización de procesos y la implementación de nuevas técnicas de trabajo.",
        date: new Date().toISOString()
    }
];

// Variable para almacenar la máquina actual seleccionada
let currentMachineId = null;

// Cargar operadores desde localStorage
function loadOperators() {
    const saved = localStorage.getItem('operators');
    if (saved) {
        operators = JSON.parse(saved);
    }
}

// Guardar operadores en localStorage
function saveOperators() {
    localStorage.setItem('operators', JSON.stringify(operators));
}

// Cargar máquinas desde localStorage
function loadMachines() {
    const saved = localStorage.getItem('machines');
    if (saved) {
        machines = JSON.parse(saved);
    }
}

// Guardar máquinas en localStorage
function saveMachines() {
    localStorage.setItem('machines', JSON.stringify(machines));
}

// Cargar reportes desde localStorage
function loadReports() {
    const saved = localStorage.getItem('reports');
    if (saved) {
        reports = JSON.parse(saved);
    }
}

// Guardar reportes en localStorage
function saveReports() {
    localStorage.setItem('reports', JSON.stringify(reports));
}

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', function() {
    loadOperators();
    loadMachines();
    loadReports();
    
    // Verificar si hay sesión activa
    const isLoggedIn = sessionStorage.getItem('isLoggedIn');
    if (isLoggedIn === 'true') {
        showScreen('menuScreen');
    }
    
    // Login form
    const loginForm = document.getElementById('loginForm');
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // Validación simple (puedes cambiar estos valores)
        if (username === 'admin' && password === 'admin123') {
            sessionStorage.setItem('isLoggedIn', 'true');
            showScreen('menuScreen');
        } else {
            alert('Usuario o contraseña incorrectos');
        }
    });
    
    // Operator form
    const operatorForm = document.getElementById('operatorForm');
    operatorForm.addEventListener('submit', function(e) {
        e.preventDefault();
        saveOperator();
    });
    
    // Machine form
    const machineForm = document.getElementById('machineForm');
    machineForm.addEventListener('submit', function(e) {
        e.preventDefault();
        saveMachine();
    });
    
    // Report form
    const reportForm = document.getElementById('reportForm');
    reportForm.addEventListener('submit', function(e) {
        e.preventDefault();
        saveReport();
    });
});

// Mostrar pantalla específica
function showScreen(screenId) {
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => screen.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
    
    // Actualizar clase del body para el fondo de login
    if (screenId === 'loginScreen') {
        document.body.className = 'login-active';
    }
}

// Funciones de navegación
function showMenu() {
    document.body.className = '';
    showScreen('menuScreen');
}

function showResults() {
    document.body.className = 'results-active';
    showScreen('resultsScreen');
    renderMachineSelection();
}

function showOperators() {
    document.body.className = 'operators-active';
    showScreen('operatorsScreen');
    renderOperators();
}

function showMachines() {
    document.body.className = 'machines-active';
    showScreen('machinesScreen');
    renderMachines();
}

// Nueva función para mostrar reportes de una máquina específica
function showMachineReports(machineId) {
    currentMachineId = machineId;
    const machine = machines.find(m => m.id === machineId);
    if (!machine) return;
    
    document.getElementById('currentMachineName').textContent = `Reportes: ${machine.name}`;
    document.body.className = 'results-active';
    showScreen('machineReportsScreen');
    renderReports();
}

function logout() {
    document.body.className = 'login-active';
    sessionStorage.removeItem('isLoggedIn');
    document.getElementById('loginForm').reset();
    showScreen('loginScreen');
}

// Actualizar estadísticas
function updateStats() {
    document.getElementById('totalOperators').textContent = operators.length;
}

// Renderizar tarjetas de operadores
function renderOperators() {
    const grid = document.getElementById('operatorsGrid');
    
    if (operators.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="icon">👤</div>
                <h3>No hay operadores registrados</h3>
                <p>Comienza agregando un nuevo operador</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = operators.map(operator => {
        // Generar iniciales para el placeholder
        const initials = operator.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        
        return `
        <div class="operator-card">
            <div class="operator-top-section">
                ${operator.photo ? 
                    `<img src="${operator.photo}" alt="${operator.name}" class="operator-photo" onclick="viewOperatorPhoto(${operator.id})" style="cursor: pointer;" title="Clic para ampliar">` :
                    `<div class="operator-photo-placeholder">${initials}</div>`
                }
                <div class="operator-header-info">
                    <div class="operator-header">
                        <div>
                            <div class="operator-name">${operator.name}</div>
                            <div class="operator-number">${operator.number}</div>
                        </div>
                        <div class="operator-actions">
                            <button class="btn-icon" onclick="editOperator(${operator.id})" title="Editar">✏️</button>
                            <button class="btn-icon" onclick="deleteOperator(${operator.id})" title="Eliminar">🗑️</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="operator-info">
                <div class="info-row">
                    <span class="info-label">Tipo de Sangre:</span>
                    <span class="blood-type">${operator.bloodType}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">RFC:</span>
                    <span class="info-value">${operator.rfc}</span>
                </div>
            </div>
            
            ${operator.description ? `
                <div class="operator-description">
                    ${operator.description}
                </div>
            ` : ''}
        </div>
    `}).join('');
}

// Vista previa de foto del operador
function previewOperatorPhoto(event) {
    const file = event.target.files[0];
    if (file) {
        // Validar tamaño (máx 2MB)
        if (file.size > 2 * 1024 * 1024) {
            alert('La imagen es demasiado grande. El tamaño máximo es 2MB.');
            event.target.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('operatorPhotoData').value = e.target.result;
            document.getElementById('operatorPhotoPreview').src = e.target.result;
            document.getElementById('operatorPhotoPreviewContainer').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
}

// Modal de operador
function showAddOperatorModal() {
    document.getElementById('modalTitle').textContent = 'Agregar Operador';
    document.getElementById('operatorForm').reset();
    document.getElementById('operatorId').value = '';
    document.getElementById('operatorPhotoData').value = '';
    document.getElementById('operatorPhotoPreviewContainer').style.display = 'none';
    document.getElementById('operatorModal').classList.add('active');
}

function closeOperatorModal() {
    document.getElementById('operatorModal').classList.remove('active');
}

// Guardar operador
function saveOperator() {
    const id = document.getElementById('operatorId').value;
    const photoData = document.getElementById('operatorPhotoData').value;
    
    const operator = {
        name: document.getElementById('operatorName').value,
        number: document.getElementById('operatorNumber').value,
        bloodType: document.getElementById('operatorBloodType').value,
        rfc: document.getElementById('operatorRFC').value.toUpperCase(),
        description: document.getElementById('operatorDescription').value
    };
    
    // Solo actualizar foto si se seleccionó una nueva
    if (photoData) {
        operator.photo = photoData;
    }
    
    if (id) {
        // Editar operador existente
        const index = operators.findIndex(op => op.id == id);
        operators[index] = { ...operators[index], ...operator };
    } else {
        // Agregar nuevo operador
        operator.id = operators.length > 0 ? Math.max(...operators.map(op => op.id)) + 1 : 1;
        if (photoData) {
            operator.photo = photoData;
        }
        operators.push(operator);
    }
    
    saveOperators();
    closeOperatorModal();
    renderOperators();
}

// Editar operador
function editOperator(id) {
    const operator = operators.find(op => op.id === id);
    if (!operator) return;
    
    document.getElementById('modalTitle').textContent = 'Editar Operador';
    document.getElementById('operatorId').value = operator.id;
    document.getElementById('operatorName').value = operator.name;
    document.getElementById('operatorNumber').value = operator.number;
    document.getElementById('operatorBloodType').value = operator.bloodType;
    document.getElementById('operatorRFC').value = operator.rfc;
    document.getElementById('operatorDescription').value = operator.description || '';
    
    // Mostrar foto existente si la tiene
    if (operator.photo) {
        document.getElementById('operatorPhotoData').value = operator.photo;
        document.getElementById('operatorPhotoPreview').src = operator.photo;
        document.getElementById('operatorPhotoPreviewContainer').style.display = 'block';
    } else {
        document.getElementById('operatorPhotoData').value = '';
        document.getElementById('operatorPhotoPreviewContainer').style.display = 'none';
    }
    
    document.getElementById('operatorModal').classList.add('active');
}

// Eliminar operador
function deleteOperator(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este operador?')) {
        operators = operators.filter(op => op.id !== id);
        saveOperators();
        renderOperators();
    }
}

// Ver foto del operador en grande
function viewOperatorPhoto(operatorId) {
    const operator = operators.find(op => op.id == operatorId);
    if (!operator || !operator.photo) return;
    
    // Crear modal para vista completa
    const modal = document.createElement('div');
    modal.className = 'image-modal active';
    modal.innerHTML = `
        <span class="image-modal-close" onclick="this.parentElement.remove()">&times;</span>
        <div style="text-align: center;">
            <img src="${operator.photo}" style="max-width: 500px; max-height: 500px; border-radius: 15px; object-fit: contain;" alt="${operator.name}">
            <div style="color: white; margin-top: 20px; font-size: 24px; font-weight: 600;">${operator.name}</div>
            <div style="color: rgba(255,255,255,0.8); margin-top: 5px; font-size: 16px;">${operator.number}</div>
        </div>
    `;
    
    // Cerrar al hacer clic fuera de la imagen
    modal.addEventListener('click', function(e) {
        if (e.target === modal || e.target.className === 'image-modal-close') {
            modal.remove();
        }
    });
    
    document.body.appendChild(modal);
}

// ============= FUNCIONES DE MÁQUINAS =============

// Renderizar tarjetas de máquinas
function renderMachines() {
    const grid = document.getElementById('machinesGrid');
    
    if (machines.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="icon">⚙️</div>
                <h3>No hay máquinas registradas</h3>
                <p>Comienza agregando una nueva máquina</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = machines.map(machine => `
        <div class="machine-card">
            <div class="machine-header">
                <div class="machine-name">${machine.name}</div>
                <div class="machine-actions">
                    <button class="btn-icon" onclick="editMachine(${machine.id})" title="Editar">✏️</button>
                    <button class="btn-icon" onclick="deleteMachine(${machine.id})" title="Eliminar">🗑️</button>
                </div>
            </div>
            
            <div class="machine-description">
                ${machine.description}
            </div>
            
            <div class="machine-manual">
                <a href="${machine.manualLink}" target="_blank" class="manual-link">
                    <span class="manual-icon">📖</span>
                    Ver Manual de Usuario
                </a>
            </div>
        </div>
    `).join('');
}

// Modal de máquina
function showAddMachineModal() {
    document.getElementById('machineModalTitle').textContent = 'Agregar Máquina';
    document.getElementById('machineForm').reset();
    document.getElementById('machineId').value = '';
    document.getElementById('machineModal').classList.add('active');
}

function closeMachineModal() {
    document.getElementById('machineModal').classList.remove('active');
}

// Guardar máquina
function saveMachine() {
    const id = document.getElementById('machineId').value;
    const machine = {
        name: document.getElementById('machineName').value,
        description: document.getElementById('machineDescription').value,
        manualLink: document.getElementById('machineManualLink').value
    };
    
    if (id) {
        // Editar máquina existente
        const index = machines.findIndex(m => m.id == id);
        machines[index] = { ...machines[index], ...machine };
    } else {
        // Agregar nueva máquina
        machine.id = machines.length > 0 ? Math.max(...machines.map(m => m.id)) + 1 : 1;
        machines.push(machine);
    }
    
    saveMachines();
    closeMachineModal();
    renderMachines();
}

// Editar máquina
function editMachine(id) {
    const machine = machines.find(m => m.id === id);
    if (!machine) return;
    
    document.getElementById('machineModalTitle').textContent = 'Editar Máquina';
    document.getElementById('machineId').value = machine.id;
    document.getElementById('machineName').value = machine.name;
    document.getElementById('machineDescription').value = machine.description;
    document.getElementById('machineManualLink').value = machine.manualLink;
    
    document.getElementById('machineModal').classList.add('active');
}

// Eliminar máquina
function deleteMachine(id) {
    if (confirm('¿Estás seguro de que deseas eliminar esta máquina?')) {
        machines = machines.filter(m => m.id !== id);
        saveMachines();
        renderMachines();
    }
}

// ============= FUNCIONES DE REPORTES =============

// Formatear fecha
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('es-MX', options);
}

// Renderizar selección de máquinas
function renderMachineSelection() {
    const grid = document.getElementById('machineSelectionGrid');
    
    if (machines.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="icon">⚙️</div>
                <h3>No hay máquinas registradas</h3>
                <p>Primero agrega máquinas en "Administrar Máquinas"</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = machines.map(machine => {
        // Contar reportes de esta máquina
        const reportCount = reports.filter(r => r.machineId === machine.id).length;
        
        return `
        <div class="machine-select-card" onclick="showMachineReports(${machine.id})">
            <div class="machine-select-icon">⚙️</div>
            <div class="machine-select-name">${machine.name}</div>
            <div class="machine-select-count">${reportCount} reporte${reportCount !== 1 ? 's' : ''}</div>
        </div>
    `}).join('');
}

// Renderizar reportes
function renderReports() {
    const grid = document.getElementById('reportsGrid');
    
    // Filtrar reportes de la máquina actual
    const machineReports = reports.filter(r => r.machineId === currentMachineId);
    
    if (machineReports.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="icon">📊</div>
                <h3>No hay reportes para esta máquina</h3>
                <p>Comienza agregando un nuevo reporte con gráficas</p>
            </div>
        `;
        return;
    }
    
    // Ordenar reportes por fecha (más reciente primero)
    const sortedReports = [...machineReports].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    grid.innerHTML = sortedReports.map(report => `
        <div class="report-card" onclick="viewReportDetail(${report.id})">
            <div class="report-image-container">
                <img src="${report.imageData}" alt="${report.title}" class="report-image">
            </div>
            <div class="report-content">
                <div class="report-header">
                    <div style="flex: 1;">
                        <div class="report-title">${report.title}</div>
                        <div class="report-date">📅 ${formatDate(report.date)}</div>
                    </div>
                    <div class="report-actions" onclick="event.stopPropagation()">
                        <button class="btn-icon" onclick="editReport(${report.id})" title="Editar">✏️</button>
                        <button class="btn-icon" onclick="deleteReport(${report.id})" title="Eliminar">🗑️</button>
                    </div>
                </div>
                <div class="report-description-preview">
                    ${report.description}
                </div>
                <span class="report-view-more">Ver más →</span>
            </div>
        </div>
    `).join('');
}

// Vista previa de imagen al seleccionar archivo
function previewReportImage(event) {
    const file = event.target.files[0];
    if (file) {
        // Validar tamaño (máx 5MB)
        if (file.size > 5 * 1024 * 1024) {
            alert('El archivo es demasiado grande. El tamaño máximo es 5MB.');
            event.target.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('reportImageData').value = e.target.result;
            document.getElementById('imagePreview').src = e.target.result;
            document.getElementById('imagePreviewContainer').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
}

// Modal de reporte
function showAddReportModal() {
    if (!currentMachineId) {
        alert('Error: No hay máquina seleccionada');
        return;
    }
    
    document.getElementById('reportModalTitle').textContent = 'Agregar Reporte';
    document.getElementById('reportForm').reset();
    document.getElementById('reportId').value = '';
    document.getElementById('reportImageData').value = '';
    document.getElementById('reportMachineId').value = currentMachineId;
    document.getElementById('imagePreviewContainer').style.display = 'none';
    document.getElementById('reportModal').classList.add('active');
}

function closeReportModal() {
    document.getElementById('reportModal').classList.remove('active');
}

// Guardar reporte
function saveReport() {
    const id = document.getElementById('reportId').value;
    const imageData = document.getElementById('reportImageData').value;
    const machineId = parseInt(document.getElementById('reportMachineId').value);
    
    // Validar que haya imagen si es nuevo reporte
    if (!id && !imageData) {
        alert('Por favor selecciona una imagen para el reporte');
        return;
    }
    
    const report = {
        title: document.getElementById('reportTitle').value,
        description: document.getElementById('reportDescription').value,
        date: new Date().toISOString(),
        machineId: machineId
    };
    
    // Solo actualizar imagen si se seleccionó una nueva
    if (imageData) {
        report.imageData = imageData;
    }
    
    if (id) {
        // Editar reporte existente
        const index = reports.findIndex(r => r.id == id);
        reports[index] = { ...reports[index], ...report };
    } else {
        // Agregar nuevo reporte
        report.id = reports.length > 0 ? Math.max(...reports.map(r => r.id)) + 1 : 1;
        report.imageData = imageData;
        reports.push(report);
    }
    
    saveReports();
    closeReportModal();
    renderReports();
    // Actualizar el contador de reportes en la pantalla de selección
    renderMachineSelection();
}

// Editar reporte
function editReport(id) {
    const report = reports.find(r => r.id === id);
    if (!report) return;
    
    document.getElementById('reportModalTitle').textContent = 'Editar Reporte';
    document.getElementById('reportId').value = report.id;
    document.getElementById('reportTitle').value = report.title;
    document.getElementById('reportDescription').value = report.description;
    document.getElementById('reportImageData').value = report.imageData;
    document.getElementById('reportMachineId').value = report.machineId;
    
    // Mostrar vista previa de la imagen existente
    document.getElementById('imagePreview').src = report.imageData;
    document.getElementById('imagePreviewContainer').style.display = 'block';
    
    document.getElementById('reportModal').classList.add('active');
}

// Eliminar reporte
function deleteReport(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este reporte?')) {
        reports = reports.filter(r => r.id !== id);
        saveReports();
        renderReports();
        // Actualizar el contador de reportes
        renderMachineSelection();
    }
}

// Ver reporte completo en modal
function viewReportDetail(reportId) {
    const report = reports.find(r => r.id == reportId);
    if (!report) return;
    
    // Crear modal para vista completa
    const modal = document.createElement('div');
    modal.className = 'image-modal active';
    modal.innerHTML = `
        <span class="image-modal-close" onclick="this.parentElement.remove()">&times;</span>
        <div class="report-detail-container">
            <img src="${report.imageData}" class="report-detail-image" alt="${report.title}">
            <div class="report-detail-content">
                <div class="report-detail-header">
                    <div class="report-detail-title">${report.title}</div>
                    <div class="report-detail-date">📅 ${formatDate(report.date)}</div>
                </div>
                <div class="report-detail-description">${report.description}</div>
            </div>
        </div>
    `;
    
    // Cerrar al hacer clic fuera del contenido
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    document.body.appendChild(modal);
}

// Cerrar modal al hacer clic fuera
window.onclick = function(event) {
    const operatorModal = document.getElementById('operatorModal');
    const machineModal = document.getElementById('machineModal');
    const reportModal = document.getElementById('reportModal');
    
    if (event.target === operatorModal) {
        closeOperatorModal();
    }
    if (event.target === machineModal) {
        closeMachineModal();
    }
    if (event.target === reportModal) {
        closeReportModal();
    }
}
