#version 330 core


in vec3 in_position;

void func(){
    gl_Position = vec4(in_position,1.0);
}

void main(){

    func();
}