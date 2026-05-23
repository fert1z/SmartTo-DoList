function validForm(event) {
    // Запускаем каждую проверку отдельно, чтобы они не блокировали друг друга
    var isPasswordMatch = confirmPasswords(event);
    var isUsernameValid = usernameValidation(event);
    var isPasswordLenValid = validatePasswordLen(event);
    var isEmailValid = valideEmail(event);

    // Если хотя бы ОДНА проверка провалилась
    if (!isPasswordMatch || !isUsernameValid || !isPasswordLenValid || !isEmailValid) {
        // На всякий случай принудительно останавливаем отправку формы
        if (event) event.preventDefault();
        return false;
    }

    // Если всё идеально, разрешаем форме спокойно уйти на сервер Flask
    return true;
}

function validatePasswordLen(event) {
    var password = document.querySelector('#password').value;
    if (password.length < 8) {
        alert('Пароль должен быть не короче 8 символов.');
        if (event) event.preventDefault();
        return false;
    }
    return true;
}

function valideEmail(event) {
    var email = document.querySelector('#email').value;
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('Введите корректный email.');
        if (event) event.preventDefault();
        return false;
    }
    return true;
}

function confirmPasswords(event) {
    var password = document.querySelector('#password').value;
    var confirmPassword = document.querySelector('#confirm_password').value;
    if (password !== confirmPassword) {
        alert('Пароли не совпадают.');
        if (event) event.preventDefault();
        return false;
    }
    return true;
}

function usernameValidation(event) {
    var username = document.querySelector('#username').value.trim();
    var usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
    if (username.length < 3) {
        alert('Имя пользователя — не менее 3 символов.');
        if (event) event.preventDefault();
        return false;
    }
    if (!usernameRegex.test(username)) {
        alert('Имя пользователя должно содержать только латинские буквы, цифры и подчеркивание (3-20 символов).');
        if (event) event.preventDefault();
        return false;
    }
    return true;
}
