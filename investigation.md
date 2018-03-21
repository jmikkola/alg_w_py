### Why does composing substitutions involve applying one substitution to the other?

Let's think about when this can happen. First, applying a substitution to
another will only do something if they are both non-empty. The only way to get a
non-empty substitution is to infer the type of an expression involving a
function application. (All other types of expressions either give an empty
substitution, or build a substitution out of their subexpressions without adding
anything to the substitution.) This is because only function applications
involve finding the most general unifier.

So, we have to get substitutions from two different function applications. There
are two ways to get two subexpressions in a single expression: a let binding,
and another function application. Let's try the later.

`let id = x.x in (id id) (id id)`

This creates the identity function and applies it to itself. It then applies the
result of applying it to itself to the result of applying it to itself.

Does this create the case that were are looking for? Let's step through the
process and find out.

First, we find the type of the let binding.

`get_type("let...", env={})`

- We get the type of the first expression (the identity function). Right now,
the type environment is empty.
- `get_type("x.x", env={})`
    - This generates a new type variable, `v0`
    - It creates a type environment `{"x": Scheme([], v0)}`
    - And uses this to find the type of the function body (`x`).
    - `get_type("x", env={"x": Scheme([], v0)})`
        - This finds the type scheme for `x` in the type environment.
        - The type scheme `Scheme([], v0)` is instantiated.
        - Since there are no bound variables, the result in just `v0`
        - This returns an empty substitution and the type `v0`
    - Back to typing the function `x.x`.
    - This applies the (empty) substitution we just got to the type variable
      created above (which happens to be the same type variable returned by
      typing the function body). This doesn't do anything to it, so it returns `v0`.
    - This then constructs a function type containing the type that was just
      substituted (`v0`) and the type of the function body (also `v0`) to get
      the type `v0 -> v0`.
    - It returns an empty substitution and the type `v0 -> v0`
- Back to typing the let binding.
- It applies the empty substitution that was just returned to the type
  environment (also empty!), resulting in another empty type environment.
- That empty type environment is used to generalize the type returned above.
    - This finds the set of free type variables in the function type (which is
      just `v0`) and removes from that the set of free type variables in the
      environment (an empty set, since the type environment is empty), resulting
      is the set `{v0}`.
    - That set is used as the bound variables for creating the type scheme
      `Scheme([v0], v0 -> v0)`.
- A new type environment is created with that generalized type
- `{"id": Scheme([v0], v0 -> v0)}`
- The substitution we got when typing the identity function (which was empty),
  is applied to the type environment, changing nothing.
- Now for the real meat of the puzzle: we start typing the function applications.
    - `get_type("(id id) (id id)", env={"id": Scheme([v0], v0 -> v0)})`
    - Let's call this the "outer" function application, and the two `(id id)`
      application the "left" and the "right" application, respectively.
    - So we're typing the outer function application.
    - This starts by creating a new type variable, `v1`.
    - It then gets the type of the left application.
        - `get_type("(id id)", env={"id": Scheme([v0], v0 -> v0)})`
        - This also starts with creating a new type variable, `v2`.
        - It also starts by finding the type of the left hand side.
            - `get_type("id", env={"id": Scheme([v0], v0 -> v0)})`
            - Looking up "id" in the type environment gives the scheme
              `Scheme([v0], v0 -> v0)`.
            - We instantiate this to create a new concrete type. Doing so
              replaces `v0` with (yet another) new type variable, `v3`.
            - This gives the type `v3 -> v3`. We return this along with an empty substitution.
        - Back to typing the left of the two copies of `(id id)`.
        - `sub1 = {}, type1 = (v3 -> v3)`
        - Before typing the right hand side (the second of the first pair of
          `id`s), it first applies the substitution `sub1` to the type
          environment. `sub1` is empty, so this doesn't do anything to it.
            - `get_type("id", env={"id": Scheme([v0], v0 -> v0)})`
            - This is similar to what we saw before, and returns `v4 -> v4`
        - Back to typing the left of the two copies of `(id id)`.
        - `sub2 = {}, type2 = (v4 -> v4)`
        - Now for the "actual type inference" part: we find the most general
          unifier of `type1` (with `sub2` applied to it) and a new type: `(v4 ->
          v4) -> v2`
            - `most_general_unifier(v3->v3, (v4->v4)->v2)`
            - This is recursive on function types, so it recurses on both sides
                - `most_general_unifier(v3, (v4->v4))`
                - `v3` is a type variable and `(v4->v4)` is not, so it binds `v3` to `(v4->v4)`
                - This returns the substitution `{v3: (v4->v4)}`
            - Before recursing on the right hand side, the substitution just
              created is applied to both right hand sides, changing them
                - from `v3` and `v2`
                - to `(v4->v4)` and `v2`
            - OK, now we recurse on the right hand side
                - `most_general_unifier((v4->v4), v2)`
                - `v2` is a type variable and `(v4->v4)` is not, so it binds
                  `v2` to `(v4->v4)`.
                - This returns the substitution `{v2: (v4->v4)}`
            - Finally, it composes those two substitutions, giving:
            - `{v2: (v4->v4), v3: (v4->v4)}`
        - Back to typing the left of the two copies of `(id id)`.
        - Now sub3 = `{v2: (v4->v4), v3: (v4->v4)}`
        - The other subs are empty, so composing all three gives the same thing.
        - Finally, the resulting type is that substitution applied to `v2`, so `(v4 -> v4)`
    - Back to typing the outer function application
    - We just got sub1=`{v2: (v4->v4), v3: (v4->v4)}` and type1=`(v4 -> v4)`
      from typing the left-hand side.
    - Applying sub1 to our type environment doesn't change it.
    - Now, the right-hand side
        - `get_type("(id id)", env={"id": Scheme([v0], v0 -> v0)})`
        - That looks familiar...
        - In fact, it's identical to what we just did for the left function
          application. The only difference is which type variables have already
          been generated.
        - Let's cheat and just use the same result as before, updating the type
          variable numbers.
        - Substitution: `{v5: (v7->v7), v6: (v7->v7)}`
        - Type: `(v7->v7)`
    - Back to typing the outer function application
    - We just got sub2=`{v5: (v7->v7), v6: (v7->v7)}` and type2=`(v7->v7)`
    - Now, time to find the most general unifier.
        - Left hand side: apply sub2 to type1. This doesn't change type1, so
          this is `(v4->v4)`.
        - Right hand side: `((v7->v7)->v1)` (we created `v1` way back at the
          start of this outer function application).
        - `most_general_unifier((v4->v4), ((v7->v7)->v1))`
            - Recurse on the left hand side:
                - `most_general_unifier(v4, (v7->v7))`
                - This returns the substitution `{v4: (v7->v7)}`
            - Apply that substitution to the right hand side and recurse
                - `most_general_unifier((v7->v7), v1)`
                - This returns the substitution `{v1: (v7 -> v7)}`
            - The result of composing those substitutions is `{v1: (v7->v7), v4: (v7->v7)}`
    - sub3=`{v1: (v7->v7), v4: (v7->v7)}`
    - Oh boy, time to compose the substitutions. I really hope that this does something useful.
        - `compose_subs(sub3, compose_subs(sub2, sub1))`
            - `compose_subs(sub2, sub1)`
                - sub1 is `{v2: (v4->v4), v3: (v4->v4)}`
                - sub2 is `{v5: (v7->v7), v6: (v7->v7)}`
                - The result is `{v2: (v4->v4), v3: (v4->v4), v5: (v7->v7), v6:
                  (v7->v7)}` (basically just concatenation)
            - sub3 is `{v1: (v7->v7), v4: (v7->v7)}`
            - The result in `{v1: (v7->v7), v4: (v7->v7), v2:
              ((v7->v7)->(v7->v7)), v3: ((v7->v7)->(v7->v7)), v5: (v7->v7), v6:
              (v7->v7)}`
            - OK, so that did update some substitutions when composing them.
    - This returns that huge substitution
- Back to typing the let binding
- This then composes the two substitutions. The first is empty, so that changes nothing.
- It returns the type `(v7 -> v7)`

So, long story short: Yes, typing `(id id) (id id)` does make composing
substitutions change things when applying one substitution to the other. I still
don't have a great sense of what that means, though.
