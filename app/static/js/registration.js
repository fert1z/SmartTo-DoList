function validForm(event) {
    return confirmPasswords(event) && UsernameValidation(event) && validatepassword(event) && valideEmail(event);
}





function validatepassword(event) {
    var password = document.querySelector("#password").value;
    var regex = /[@#$%&!/]/;
    var notregex = /[+=-_({})*^;:,.?"'| ]/;

    if (!regex.test(password) ) {
        alert("Password must contain at least one special character (@, #, $, %, &, !, /)");
        if (event) {
            event.preventDefault();
        }
        return false; 
    }

    if (notregex.test(password)) {
        alert("Password cannot contain the following characters: +, =, -, _, (, {, }, ), *, ^, ;, :, ,, ., ?, \", ', |");
        if (event) {
            event.preventDefault();
        }
        return false;
    }
    
    if (password.length < 8){
        alert("Password must be at least 8 characters long!");
        if (event) {
            event.preventDefault();
        }
        return false;
    }

    return true;
}

function valideEmail(event) {
    var email = document.querySelector("#email").value;
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!emailRegex.test(email)) {
        alert("Please enter a valid email address!");
        if (event) {
            event.preventDefault();
        }
        return false;
    }
    
    return true;
}


function confirmPasswords(event) {

    var password = document.querySelector("#password").value;
    var confirmPassword = document.querySelector("#confirm_password").value;


    if (password != confirmPassword){
        alert("Passwords do not match!");
        if (event) {
            event.preventDefault();
        }
        return false;
    }

    return true;
} 

function UsernameValidation(event) {

    var username = document.querySelector("#username").value;

    if (username.length < 6){
        alert("Username must be at least 6 characters long!");
        if (event) {
            event.preventDefault();
        }
        return false;
    }

    return true;
}