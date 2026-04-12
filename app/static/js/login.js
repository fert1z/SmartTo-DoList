function validLogin(event) {
    return validatePassword(event) && validateUsername(event);
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
