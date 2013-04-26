import random
import math
from fractions import Fraction

def test_relinearize(s, svars, q, n):
  si_subs, sisj_subs = generate_substitutions(s, s, svars, q, n)
  print "\n\n\nEncryption of 1:"
  _,f1 = encrypt(1, s, svars, q)
  print f1
  print "\nEncryption of 0:"
  _,f2 = encrypt(0, s, svars, q)
  print f2
  print "\nEncryption of 0 + 1:"
  fadd = f1+f2
  print fadd
  print "\nDecrypted:", decrypt(fadd, s)

  print "\n\nEncryption of 0 * 1:"
  fmult = f1 * f2
  print fmult
  print "\nRelinearized:"
  f3 = relinearize(f1*f2, svars, n, q, si_subs, sisj_subs)
  f3 = relinearize(f3, svars, n, q, si_subs, sisj_subs)
  print f3

  print "\nDecrypted:", decrypt(f3, s)

# adjusts q, n to the appropriate multiplication depth
# this probably isn't quite what we want
def adjust(q, n, depth):
  return (q>>depth), (n-depth)

def main():
  # public info 
  q = 2**10
  n = 3
  L = 2 #depth of circuit

  # private info
  keys, varnames, linsubs, quadsubs, modsubs = [], [], [], [], []

  olds, oldsvars = None, None
  for i in range(L):
    print i
    p, k = adjust(q, n, i)
    s, svars = keygen(k, p, chr(ord('a')+i))

    # re-linearization substitutions, using circular security
    si_subs, sisj_subs = generate_substitutions(s, s, svars, p, k)

    keys.append(s)
    varnames.append(svars)
    linsubs.append(si_subs)
    quadsubs.append(sisj_subs)

    # we don't need to generate any substitutions
    if i == 0:
      olds, oldsvars = s, svars
      continue

    oldp, oldk = adjust(q, n, i-1)

    # mod reduction substitutions
    mr_subs = generate_MR_substitutions(olds, s, svars, oldp, p, oldk, k)

    modsubs.append(mr_subs)
    olds, oldsvars = s, svars

  # this is public info!
  substitutions = {'varnames':varnames,'linsubs':linsubs,'quadsubs':quadsubs,'modsubs':modsubs}
  substitutions['p'] = [adjust(q, n, i)[0] for i in range(L)]
  substitutions['k'] = [adjust(q, n, i)[1] for i in range(L)]
  print substitutions

  test_relinearize(keys[0], varnames[0], q, n)
  return

  s, svars = keygen(n, q, "s")
  print "\nTesting Mod Reduction"
  _,f1 = encrypt(1, s, svars, q)
  print "\nEncryption of 1:"
  print f1
  print "\nModulus Switching"
  p = q>>8
  k = n-2

  z = randlist(p, k)
  zvars = PolynomialRing(Integers(p), k, "z").gens()
  si_subs = generate_MR_substitutions(s, z, zvars, q, p, n, k)
  fmod = modulusReduction(f1, svars, n, q, si_subs)


  s, svars = keygen(n, q, "s")
  print "\nTesting Mod Reduction"
  _,f1 = encrypt(1, s, svars, q)
  print "\nEncryption of 1:"
  print f1
  print "\nModulus Switching"
  p = q>>8
  k = n-2

  z = randlist(p, k)
  zvars = PolynomialRing(Integers(p), k, "z").gens()
  si_subs = generate_MR_substitutions(s, z, zvars, q, p, n, k)
  fmod = modulusReduction(f1, svars, n, q, si_subs)
  print "\nMod Switched"
  print fmod
  print "\nDecrypted:", decrypt(fmod, z)
  #return
  print "\nTesting Modulus Dimension Reduction"
  for i in range(40):
    _,f1 = encrypt(1, s, svars, q)
    z = randlist(p, k)
    zvars = PolynomialRing(Integers(p), k, "z").gens()
    si_subs = generate_MR_substitutions(s, z, zvars, q, p, n, k)
    fmod = modulusReduction(f1, svars, n, q, si_subs)

    #print decrypt(fmod,z)
    if(decrypt(fmod, z) != 1):
      print "fail!"
      break
    if i == 39:
      print "success!"


#keyname must be a string, the same as the polynomial variable (aka, "s" or "t" or etc.)
def keygen(n, q, keyname):
  pk = randlist(q, n)
  pk_vars = sage.rings.polynomial.polynomial_ring_constructor.PolynomialRing(Integers(q), n, keyname).gens()
  return pk, pk_vars

# TODO: needs access to si_subs, sisj_subs, level
# so that we can do re-linearize and mod-switch
def fhe_mult(f1, f2, d1, d2, subs):
  if d1 != d2:
    print 'put them on the same level'
  else:
    fmult = f1*f2
    fmult = relinearize(fmult, subs['varnames'][d], subs['k'][d], subs['p'][d], subs['linsubs'][d], subs['quadsubs'][d])
    fmult = modulusReduction(fmult, subs['varnames'][d], subs['k'][d], subs['p'][d], subs['modsubs'][d])
    return fmult

def fhe_add(f1, f2):
  return f1+f2

# take in a key vector, generate encryptions for all s[i] and s[i]s[j]
# s is old key, t is new key
def generate_substitutions(s, t, tvars, q, n):
  logq = int(math.floor(math.log(q, 2)))
  si_subs = []
  sisj_subs = []
  # encrypt each s[i]
  for i in range(len(s)):
    _,f = encrypt(s[i], t, tvars, q)
    si_subs.append(f)
  # encrypt each s[i]s[j]
  for i in range(len(s)):
    sisj_subs.append([])
    for j in range(i+1):
      sisj_subs[i].append([])
      for tau in range(logq):
        _,f = encrypt((2**tau)*s[i]*s[j], t, tvars, q)
        sisj_subs[i][j].append(f)
  return si_subs, sisj_subs

def generate_MR_substitutions(s, t, tvars, q, p, n, k):
  logq = int(math.floor(math.log(q,2)))
  si_subs = []
  # encrypt 2**tau s[i]
  for i in range(len(s)):
    si_subs.append([])
    for tau in range(logq):
      m = Fraction(p * (2**tau) * s[i], q)
      _,f = MR_encrypt(m, t, tvars, q, p)
      si_subs[i].append(f)
  return si_subs

def generate_error(q):
  return random.randint(0, q)

def dot(v1, v2):
  sum = 0
  for i in range(len(v1)):
    sum += v1[i] * v2[i]
  return sum

def randlist(q, n):
  return [random.randint(0, q) for i in range(n)]

# encrypt the bit m
def encrypt(m, s, svars, q):
  logq = int(math.floor(math.log(q,2)))
  a = randlist(q, len(s))
  e = generate_error(logq)
  b = dot(a, s) + 2*e + int(round(m))
  return (a, b), b - dot(a, svars)

# did some weird stuff to make sure we don't round too soon
def MR_encrypt(m, t, tvars, q, p):
  logp = int(math.floor(math.log(p,2)))
  a = randlist(p, len(t))
  e = generate_error(logp)
  b = Fraction(q,p) * (dot(a, t) + e + m)
  return (a, b), int(b) - int(Fraction(q,p)) * dot(a, tvars)

# decrypt the ciphertext c
def decrypt(c, key):
  return c(key).lift() % 2

# server side functions
def relinearize(f, svars, n, q, si_subs, sisj_subs):
  logq = int(math.floor(math.log(q,2)))
  g = f([0 for i in range(n)])
  for i in range(n):
    hi = f.coefficient(svars[i])([0]*n)
    g += hi*si_subs[i]
  for i in range(n):
    for j in range(i+1):
      hij = f.coefficient(svars[i]*svars[j])([0]*n)
      for tau in range(logq):
        hbit = (int(hij) >> tau) % 2
        g += hbit*sisj_subs[i][j][tau]
  return g

# The goal of this function is to tak a ciphertext (n, logq)
# and convert it to a ciphertext (k, logp) where k<n and p<q
# k ~ lambda, p = poly(k).

# To do this properly, we need to set our parameters according
# to page 7 paragraph 1
def modulusReduction(f, svars, n, q, si_subs):
  logq = int(math.floor(math.log(q,2)))
  g = f([0 for i in range(n)]).lift()
  for i in range(n):
    hi = f.coefficient(svars[i])([0]*n)
    for tau in range(logq):
      hbit = (int(hi) >> tau) % 2
      g += hbit*si_subs[i][tau]
  return g

if __name__ == '__main__':
  main()
