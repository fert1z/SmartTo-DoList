function validLogin(event) {
    return validatePassword(event) && validateUsername(event);
}




function validatePassword(event) {
    var password = document.querySelector("#password").value;
    
    if (password.length < 6) {
        alert("Password must be at least 6 characters long.");
        if (event) {
            event.preventDefault();
        }
        return false;
    }
    
    return true;
}

function validateUsername(event) {
    var username = document.querySelector("#username").value;
    if (username.length < 5){
        alert("Username must be at least 5 characters long.");
        if (event) {
            event.preventDefault();
        }
        return false;   
    }
    return true;
}
