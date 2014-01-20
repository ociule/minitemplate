from template import Template

if __name__ == "__main__":
    f = open('test.tmpl', "r")
    t = Template(f)
    print t
