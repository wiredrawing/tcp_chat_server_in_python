def add_decoration(param):
    def wrapper(f):
        print("param =>" + param);

        def new_function():
            print("関数を作り直す")

        return new_function

    return wrapper;


@add_decoration("parameters")
def decoration_method():
    print("This is decoration method");


decoration_method();
