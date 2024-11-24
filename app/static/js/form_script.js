// Функция для отправки данных в формате JSON
function sendFormData(formId, url, method) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const jsonData = {};

    formData.forEach((value, key) => {
        jsonData[key] = value;
    });

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jsonData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        alert(JSON.stringify(data, null, 2));  // Выводим результат на экран
    })
    .catch((error) => {
        console.error('Error:', error);
        alert('Error: ' + error);
    });
}

// Обработчик для формы Set Limit
document.getElementById("set-limit-form").addEventListener("submit", function(event) {
    event.preventDefault();  // Отменяем стандартную отправку формы
    sendFormData("set-limit-form", "/set_limit", "POST");
});

// Обработчик для формы Get Stats
document.getElementById("get-stats-form").addEventListener("submit", function(event) {
    event.preventDefault();  // Отменяем стандартную отправку формы
    const serviceId = document.getElementById("get_service_id").value;  // Используем новый id
    fetch(`/get_stats?service_id=${serviceId}`)
        .then(response => response.json())
        .then(data => {
            console.log('Stats:', data);
            alert(JSON.stringify(data, null, 2));
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error: ' + error);
        });
});


// Обработчик для формы Reset
document.getElementById("reset-form").addEventListener("submit", function(event) {
    event.preventDefault();  // Отменяем стандартную отправку формы
    sendFormData("reset-form", "/reset", "POST");
});
