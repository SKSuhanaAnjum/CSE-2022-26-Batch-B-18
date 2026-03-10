drop database if exists plastic ;
create database plastic ;
use plastic ;

create table users (
    id INT PRIMARY KEY AUTO_INCREMENT, 
    name VARCHAR(225),
    email VARCHAR(50), 
    password VARCHAR(50)
    );
