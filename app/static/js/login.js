function validLogin(event) {
    var isPasswordValid = validatePassword(event);
    var isUsernameValid = validateUsername(event);

    // Если хоть одно поле пустое — принудительно стопаем отправку
    if (!isPasswordValid || !isUsernameValid) {
        if (event) event.preventDefault();
        return false;
    }

    // Если всё заполнено, даем форме штатно уйти на сервер
    return true;
}

function validatePassword(event) {
    var password = document.querySelector('#password').value;
    if (password.length < 1) {
        alert('Введите пароль.');
        if (event) event.preventDefault();
        return false;
    }
    return true;
}

function validateUsername(event) {
    var username = document.querySelector('#username').value.trim();
    if (username.length < 1) {
        alert('Введите имя пользователя.');
        if (event) event.preventDefault();
        return false;
    }
    return true;
}
