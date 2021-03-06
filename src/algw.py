

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
            # No substitution needed, the type for this has already
            # been substituted in wherever needed.
            # Instantiate the type scheme so that this can be a subtype
            # of the actual type.
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
        # Add the variable "x" to the type environment,
        # just bound to a new typevar.
        tvar = TVar(type_inference.new_type_var())
        tenv0 = tenv.remove(self.x)
        tenv1 = tenv0.add(self.x, Scheme([], tvar))

        # Use that environment to get the type of the function body
        sub1, type1 = self.expr.get_type(tenv1, type_inference)

        # Typing the function body may restrict the type of the argument
        # to more specific than just a var, so apply the substitution
        # to that argument before building the function type.
        return sub1, TFunc(tvar.apply_sub(sub1), type1)


class EApp(Expression):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def show(self):
        return '(' + self.e1.show() + ' ' + self.e2.show() + ')'

    def get_type(self, tenv, type_inference):
        # Making a generic instance of the function's type here isn't necessary
        # because that already happens when typing the variable that evaluates
        # to the function.

        # Generate the tvar now just to make the numbering make sense:
        tvar = TVar(type_inference.new_type_var())

        # First, find the type of the function.
        sub1, type1 = self.e1.get_type(tenv, type_inference)
        # Finding that type may have resulted in substitutions that apply
        # to the argument (e.g. if the function closes over a variable that is
        # also used in the argument expression), so apply that substitution
        # to the type env before getting the type of the argument.
        sub2, type2 = self.e2.get_type(tenv.apply_sub(sub1), type_inference)

        # We use tvar to represent the return type of the function in this
        # particular instance.
        # sub2 is applied to type1 in case that further narrows the type.
        sub3 = type_inference.most_general_unifier(
            type1.apply_sub(sub2), TFunc(type2, tvar)
        )

        # The resulting substitution needs to take all three substitutions
        # into account.
        sub = compose_subs(sub3, compose_subs(sub2, sub1))
        # Apply sub3 to tvar to find out what the type actually is
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
        # First, get the type of the first expression in the current
        # environment (which may have a different binding for x,
        # so we don't remove x from tenv just yet).
        sub1, type1 = self.e1.get_type(tenv, type_inference)

        # Apply sub1 to create a new type env with what we just learned,
        # and use that to figure out how to generalize type1 into a
        # type scheme.
        type1_sub = tenv.apply_sub(sub1).generalize(type1)
        # Create a new type environment where x is bound to that type scheme.
        tenv1 = tenv.add(self.x, type1_sub)

        # Use that new type env (with sub1 applied to it) to find the type
        # of the inner expression.
        tenv1_sub = tenv1.apply_sub(sub1)
        sub2, type2 = self.e2.get_type(tenv1_sub, type_inference)
        # The resulting substitution takes both of the other substitutions
        # into account.
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

    def __repr__(self):
        return str(self)


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

    def __str__(self):
        return 'TVar({})'.format(self.name)

    def __repr__(self):
        return 'TVar({!r})'.format(self.name)


class TInt(Type):
    def show(self):
        return 'Int'

    def __str__(self):
        return 'TInt()'


class TFloat(Type):
    def show(self):
        return 'Float'

    def __str__(self):
        return 'TFloat()'


class TFunc(Type):
    def __init__(self, left, right):
        if not isinstance(left, Type):
            raise Exception(left)
        if not isinstance(right, Type):
            raise Exception(right)
        self.left = left
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

    def __repr__(self):
        return 'TFunc({}, {})'.format(self.left, self.right)


class Scheme:
    '''
    A type scheme is just a type with some extra information
    (a set of type variables) attached.

    That set of type variables influnces the free_type_variables
    and apply_sub operations, and makes the instantiate operation
    possible.
    '''
    def __init__(self, bound, t):
        self.bound = set(bound)
        self.t = t

    def free_type_variables(self):
        '''
        This is every free type variable in the type
        that doesn't appear in the bound set.
        '''
        return self.t.free_type_variables() - self.bound

    def apply_sub(self, sub):
        '''
        This applies a substitution to the type,
        skipping any substitution of a variable in the bound set.
        '''
        smaller_sub = {
            v: t
            for v, t in sub.items()
            if v not in self.bound
        }
        ts = self.t.apply_sub(smaller_sub)
        return Scheme(self.bound, ts)

    def instantiate(self, type_inference):
        '''
        This creates a new polymorphic instance of the type.

        For example, if the type is (a -> a), this would
        create (b -> b), allowing it to be unified against
        (int -> c) to find that b and c are int without
        changing the type of a.
        '''
        sub = {
            var: TVar(type_inference.new_type_var())
            for var in self.bound
        }
        return self.t.apply_sub(sub)

    def __str__(self):
        return 'Scheme({}, {})'.format(self.bound, self.t.show())

    def __repr__(self):
        return str(self)


def compose_subs(s1, s2):
    out = {v: t for v, t in s1.items()}
    for v, t in s2.items():
        out[v] = t.apply_sub(s1)
    return out


class TypeEnv:
    '''
    A type environment is a mapping from variable name
    (variable in the program, not type variable) to
    type schemes.
    '''
    def __init__(self, schemes):
        self.schemes = schemes

    def free_type_variables(self):
        '''
        Returns the union of all the free type variables
        for each scheme.
        '''
        ftvs = set()
        for scheme in self.schemes.values():
            ftvs = ftvs | scheme.free_type_variables()
        return ftvs

    def apply_sub(self, sub):
        '''
        Applies a substitution to all the schemes.
        '''
        return TypeEnv({
            v: scheme.apply_sub(sub)
            for v, scheme in self.schemes.items()
        })

    def remove(self, var):
        ''' Removes a binding '''
        return TypeEnv({
            v: scheme
            for v, scheme in self.schemes.items()
            if v != var
        })

    def add(self, var, scheme):
        ''' Adds a binding '''
        copy = {v: s for v, s in self.schemes.items()}
        copy[var] = scheme
        return TypeEnv(copy)

    def generalize(self, t):
        '''
        Generalizes the type t into a type scheme by looking at what
        type variables are free in the type and not in the environment.
        '''
        bound_vars = t.free_type_variables() - self.free_type_variables()
        return Scheme(bound_vars, t)

    def __contains__(self, name):
        return name in self.schemes

    def __getitem__(self, name):
        return self.schemes[name]

    def __str__(self):
        return 'TypeEnv({})'.format(self.schemes)


class TypeInference:
    def __init__(self):
        self._next_tvar_n = 0

    def new_type_var(self):
        ''' Generates a new type variable on each call '''
        tvar = 'tv_' + str(self._next_tvar_n)
        self._next_tvar_n += 1
        return tvar

    def most_general_unifier(self, t1, t2):
        '''
        Either finds a substitution such that
        t1.apply_sub(sub) == t2.apply_sub(sub)
        or throws an exception.
        '''
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
        '''
        Creates a substitution from name to t
        after checking that name isn't free in t
        (which would lead to an infinite type)
        '''
        if not isinstance(t, Type):
            raise Exception(t)
        if isinstance(t, TVar) and t.name == name:
            return {}
        if name in t.free_type_variables():
            raise Exception('Occur check fails')
        return {name: t}


def infer_type(expr, starting_env=None):
    if starting_env is None:
        starting_env = {}

    type_inference = TypeInference()
    tenv = TypeEnv(starting_env)
    sub, typ = expr.get_type(tenv, type_inference)
    return typ.apply_sub(sub)


def main():
    expr1 = ELet('id', EAbs('x', EVar('x')),
                 EVar('id'))
    print(infer_type(expr1).show())

    expr2 = EAbs(
        'x',
        ELet(
            'y', EApp(EVar('id'), EVar('x')),
            EApp(EVar('inc'), EVar('x'))
        )
    )
    env2 = {
        'id': Scheme(['a'], TFunc(TVar('a'), TVar('a'))),
        'inc': Scheme([], TFunc(TInt(), TInt())),
    }
    print(infer_type(expr2, starting_env=env2).show())

    expr3 = EAbs(
        'x',
        ELet(
            'y', EApp(EVar('inc'), EVar('x')),
            EVar('x')
        )
    )
    env3 = {
        'inc': Scheme([], TFunc(TInt(), TInt())),
    }
    print(infer_type(expr3, starting_env=env3).show())

    big_id = ELet(
        'id', EAbs('x', EVar('x')),
        EApp(
            EApp(EVar('id'), EVar('id')),
            EApp(EVar('id'), EVar('id'))
        )
    )
    print('big_id:', infer_type(big_id, starting_env={}).show())

    # Polymorphic let binding:
    expr4 = ELet(
        'id', EAbs('x', EVar('x')),
        ELet(
            'y', EApp(EVar('id'), ELit(LFloat(0.123))),
            EApp(EVar('id'), ELit(LInt(123)))
        )
    )
    print(infer_type(expr4).show())


if __name__ == '__main__':
    main()
