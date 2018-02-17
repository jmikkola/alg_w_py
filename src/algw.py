

class Expression:
    pass


class EVar(Expression):
    def __init__(self, name):
        self.name = name

    def show(self):
        return self.name

    def get_type(self, tenv, type_inference):
        if self.name in tenv:
            sigma = tenv[self.name]
            return {}, sigma.instantiate(type_inference)
        raise Exception('unbound variable: ' + self.name)


class ELit(Expression):
    def __init__(self, lit):
        self.lit = lit

    def show(self):
        return self.lit.show()

    def get_type(self, tenv, type_inference):
        return self.lit.get_type(tenv, type_inference)


class EAbs(Expression):
    def __init__(self, x, expr):
        self.x = x
        self.expr = expr

    def show(self):
        return '(lambda [{x}] {expr})'.format(x=self.x, expr=self.expr.show())

    def get_type(self, tenv, type_inference):
        tvar = TVar(type_inference.new_type_var())
        tenv0 = tenv.remove(self.x)
        tenv1 = tenv0.add(self.x, Scheme([], tvar))
        sub1, type1 = self.expr.get_type(tenv1, type_inference)
        # TODO: Why apply sub here?
        return sub1, TFunc(tvar.apply_sub(sub1), type1)


class EApp(Expression):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def show(self):
        return '(' + self.e1.show() + ' ' + self.e2.show() + ')'

    def get_type(self, tenv, type_inference):
        tvar = TVar(type_inference.new_type_var())
        sub1, type1 = self.e1.get_type(tenv, type_inference)
        # TODO: Again, why apply that sub?
        sub2, type2 = self.e2.get_type(tenv.apply_sub(sub1), type_inference)
        sub3 = type_inference.most_general_unifier(
            type1.apply_sub(sub2), TFunc(type2, tvar)
        )
        sub = compose_subs(sub3, compose_subs(sub2, sub1))
        return sub, tvar.apply_sub(sub3)


class ELet(Expression):
    def __init__(self, x, e1, e2):
        self.x = x
        self.e1 = e1
        self.e2 = e2

    def show(self):
        return '(let [{x} {e1}] {e2})'.format(
            x=self.x, e1=self.e1.show(), e2=self.e2.show())

    def get_type(self, tenv, type_inference):
        sub1, type1 = self.e1.get_type(tenv, type_inference)

        type1_sub = tenv.apply_sub(sub1).generalize(type1)
        tenv1 = tenv.add(self.x, type1_sub)

        sub2, type2 = self.e2.get_type(tenv1.apply_sub(sub1), type_inference)
        return compose_subs(sub1, sub2), type2


class Literal:
    pass


class LInt(Literal):
    def __init__(self, i):
        self.i = i

    def get_type(self, tenv, type_inference):
        return {}, TInt()


class LFloat(Literal):
    def __init__(self, f):
        self.f = f

    def get_type(self, tenv, type_inference):
        return {}, TFloat()


class Type:
    def free_type_variables(self):
        return set()

    def apply_sub(self, sub):
        return self


class TVar(Type):
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, TVar) and other.name == self.name

    def free_type_variables(self):
        return set([self.name])

    def apply_sub(self, sub):
        if self.name in sub:
            return sub[self.name]
        return self

    def show(self):
        return self.name


class TInt(Type):
    def show(self):
        return 'Int'


class TFloat(Type):
    def show(self):
        return 'Float'


class TFunc(Type):
    def __init__(self, left, right):
        if not isinstance(left, Type):
            raise Exception(left)
        if not isinstance(right, Type):
            raise Exception(right)
        self.left = right
        self.right = right

    def __eq__(self, other):
        if not isinstance(other, TFunc):
            return False
        return other.left == self.left and other.right == self.right

    def free_type_variables(self):
        return self.left.free_type_variables() | self.right.free_type_variables()

    def apply_sub(self, sub):
        left_s = self.left.apply_sub(sub)
        right_s = self.right.apply_sub(sub)
        return TFunc(left_s, right_s)

    def show(self):
        return self.left.show() + ' -> ' + self.right.show()


class Scheme:
    def __init__(self, bound, t):
        self.bound = set(bound)
        self.t = t

    def free_type_variables(self):
        return self.t.free_type_variables() - self.bound

    def apply_sub(self, sub):
        smaller_sub = {
            v: t
            for v, t in sub.items()
            if v not in self.bound
        }
        ts = self.t.apply_sub(smaller_sub)
        return Scheme(self.bound, ts)

    def instantiate(self, type_inference):
        sub = {
            var: TVar(type_inference.new_type_var())
            for var in self.bound
        }
        return self.t.apply_sub(sub)

    def __str__(self):
        return 'Scheme({}, {})'.format(self.bound, self.t.show())


def compose_subs(s1, s2):
    '''
    The logic here is pretty unclear to me
    '''
    out = {v: t for v, t in s1.items()}
    for v, t in s2.items():
        out[v] = t.apply_sub(s1)
    return out


class TypeEnv:
    def __init__(self, schemes):
        self.schemes = schemes

    def free_type_variables(self):
        ftvs = set()
        for scheme in self.schemes.values():
            ftvs = ftvs | scheme.free_type_variables()
        return ftvs

    def apply_sub(self, sub):
        ''' I'm not sure I get what it means to apply a
        substitution to a type env '''
        return TypeEnv({
            v: scheme.apply_sub(sub)
            for v, scheme in self.schemes.items()
        })

    def remove(self, var):
        return TypeEnv({
            v: scheme
            for v, scheme in self.schemes.items()
            if v != var
        })

    def add(self, var, scheme):
        copy = {v: s for v, s in self.schemes.items()}
        copy[var] = scheme
        return TypeEnv(copy)

    def generalize(self, t):
        ''' This I only vaguely understand '''
        bound_vars = t.free_type_variables() - self.free_type_variables()
        return Scheme(bound_vars, t)

    def __contains__(self, name):
        return name in self.schemes

    def __getitem__(self, name):
        return self.schemes[name]


class TypeInference:
    def __init__(self):
        self._next_tvar_n = 0

    def new_type_var(self):
        tvar = 'tv_' + str(self._next_tvar_n)
        self._next_tvar_n += 1
        return tvar

    def most_general_unifier(self, t1, t2):
        if isinstance(t1, TFunc) and isinstance(t2, TFunc):
            s1 = self.most_general_unifier(t1.left, t2.left)
            s2 = self.most_general_unifier(
                t1.right.apply_sub(s1),
                t2.right.apply_sub(s1),
            )
            return compose_subs(s1, s2)
        elif isinstance(t1, TVar):
            return self.var_bind(t1.name, t2)
        elif isinstance(t2, TVar):
            return self.var_bind(t2.name, t1)
        elif isinstance(t1, TInt) and isinstance(t2, TInt):
            return {}
        elif isinstance(t1, TFloat) and isinstance(t2, TFloat):
            return {}
        else:
            raise Exception('cannot unify {} and {}'.format(t1, t2))

    def var_bind(self, name, t):
        if not isinstance(t, Type):
            raise Exception(t)
        if isinstance(t, TVar) and t.name == name:
            return {}
        if name in t.free_type_variables():
            raise Exception('Occur check fails')
        return {name: t}


def infer_type(expr):
    type_inference = TypeInference()
    tenv = TypeEnv({})
    sub, typ = expr.get_type(tenv, type_inference)
    return typ.apply_sub(sub)


def main():
    expr1 = ELet('id', EAbs('x', EVar('x')),
                 EVar('id'))
    print(infer_type(expr1).show())


if __name__ == '__main__':
    main()
