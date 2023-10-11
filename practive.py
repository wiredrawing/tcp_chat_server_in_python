import unicodedata


def show_message(f):
    def wrapper():
        print("(1).This is decorator");
        return f();

    return wrapper


def add_function(f):
    def wrapper():
        print("(2).Add one more function .");
        return f();

    return wrapper


# デコレータを2つ重ねる
@show_message
@add_function
def a_method():
    print("(3).The method which do something.");
    pass


a_method();


def outer(param):
    def inner(inner_param):
        nonlocal param;
        param += 1;
        print(param)
        # print(inner_param)
        pass

    return inner;


a = 1;
b = outer(a);
b(0);
b(0);
b(0);
b(0);
b(0);
b(0);
b(0);

sentence = "１２３４５６７８９ｱｲｳｴｵカキクケコ麵"

converted_sentence = unicodedata.normalize("NFKC", sentence);
print(sentence);
print(converted_sentence);


class SuperClass:

    def __init__(self):
        print("This is construct");

    def method_a(self):
        print(self);
        print("This is the method named 'method_a'");


class ChildClass(SuperClass):

    def __init__(self):
        super().__init__()

    def method_b(self):
        print(self);
        print("This is a method named 'method_b'");

    def method_a(self):
        print("Overriding a method named 'method_a'")
        super().method_a();


obj = ChildClass();
obj.method_b();
obj.method_a();
