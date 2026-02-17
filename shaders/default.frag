#version 330 core


out vec4 fragColor;

void func(){
// RGBA Color: Red=1.0, Green=0, Blue=0, Alpha=1.0
    fragColor = vec4(1.0,0.0,0.0,1.0);
}

void main(){

    func();
    
}