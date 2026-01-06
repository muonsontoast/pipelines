function dls_bts(varargin)
% 
% DIAMOND BTS
% for the AT; RB 18/04/2005
%
%
% Initial parameters at upstream end of booster FQUAD
% values found for booster at tune point .18/.27 (measured value on 21/01/2018)
% Beta_x = 12.265793630021296;   
% Beta_y = 2.900312598824513;
% Alpha_y = -2.962439696916365;
% Alpha_x = 0.739610134929706;
% Dispersion_x = 1.198725891655882;
% Dispersion_xp = 0.317780064117268;

if nargin > 0
    mode = varargin{1};
else
    mode = 'prezepto';
end

testmode = 1;   % Flag for BTS test stand

global THERING GLOBVAL

GLOBVAL.E0 = 3e9;
GLOBVAL.LatticeFile = 'BTS';

disp(' ');
disp('** Loading DIAMOND BTS **');

% AP  =  {ataperture('AP', [-0.05, 0.05, -0.05, 0.05],'AperturePass')};
% Markers for test stand
WP      = {atmarker('WPOINT', 'IdentityPass')};
VSCREEN = {atmarker('SCREEN', 'IdentityPass')};
OTR     = {atmarker('SCREEN', 'IdentityPass')};
CERN_CH1 = {atmarker('SCREEN', 'IdentityPass')}; 
% drifts
BPM     = {atdrift('BBPM', .05E+00,'DriftPass')};
BPMSEP  = {atdrift('BPMSEP', .27E+00,'DriftPass')};
BPMSEP1  = {atdrift('BPMSEP1', .2035E+00,'DriftPass')};
BSEPTTOQA   = {atdrift('BSEPTTOQA', .53E+00,'DriftPass')};
BSEPTTOQBa   = {atdrift('BSEPTTOQBa',0.530E+00,'DriftPass')};
BSEPTTOQBb   = {atdrift('BSEPTTOQBb',1.575E+00,'DriftPass')};
BR03CDIOTR03 = {atmarker('BR03CDIOTR03', 'IdentityPass')};
BSEPTTOQB = [BSEPTTOQBa BR03CDIOTR03 BSEPTTOQBb];
BSEPTTOQC   = {atdrift('BSEPTTOQC', .1755E+00,'DriftPass')};
CORRSEP = {atdrift('CORRSEP', .3E+00,'DriftPass')};
DFT10   = {atdrift('DFT10', .01E+00,'DriftPass')};
DFT120  = {atdrift('DFT120', .12E+00,'DriftPass')};
DFT1530 = {atdrift('DFT1520', 1.53E+00,'DriftPass')};
DFT180  = {atdrift('DFT180', .18E+00,'DriftPass')};
DFT200  = {atdrift('DFT200', .2E+00,'DriftPass')};
DFT2170 = {atdrift('DFT2170', 2.17E+00,'DriftPass')};
DFT250  = {atdrift('DFT250', .25E+00,'DriftPass')};
DFT300  = {atdrift('DFT300', .3E+00,'DriftPass')};
DFT520  = {atdrift('DFT520', .52E+00,'DriftPass')};
DFT580  = {atdrift('DFT580', .58E+00,'DriftPass')};
DFT60   = {atdrift('DFT60', .06E+00,'DriftPass')};
MMS   = {atdrift('MMS', .0E+00,'DriftPass')};
MPS   = {atdrift('MPS', .0E+00,'DriftPass')};
PSTRAIGHT1  = {atdrift('PSTRAIGHT1',0.5,'DriftPass')};
PSTRAIGHT2  = {atdrift('PSTRAIGHT2',1.864,'DriftPass')};
PSTRAIGHT3  = {atdrift('PSTRAIGHT3',0.5,'DriftPass')};
PSTRAIGHT4A = {atdrift('PSTRAIGHT4Aa',0.299,'DriftPass')};
PSTRAIGHT4Ba = {atdrift('PSTRAIGHT4B',1.205,'DriftPass')};
PSTRAIGHT4Bb = {atdrift('PSTRAIGHT4Bb',2.434,'DriftPass')};
BSDIOTR = {atmarker('BSDIOTR', 'IdentityPass')};
PSTRAIGHT4B = [PSTRAIGHT4Ba BSDIOTR PSTRAIGHT4Bb];
PSTRAIGHT4C = {atdrift('PSTRAIGHT4C',0.176,'DriftPass')};
PSTRAIGHT5  = {atdrift('PSTRAIGHT5',0.5,'DriftPass')};

if testmode == 1
    
    PS6A11      = {atdrift('PS6A1',1.12,'DriftPass')};
    PS6A12      = {atdrift('PS6A1',1.00,'DriftPass')};
    PS6A2       = {atdrift('PS6A2',0.154*2,'DriftPass')};
    PS6A2a      = {atdrift('PS6A2',0.1124,'DriftPass')};
    PS6A2b      = {atdrift('PS6A2',0.1956,'DriftPass')};
    PS6A4       = {atdrift('PS6A4',0.21,'DriftPass')};
    PS6A5       = {atdrift('PS6A5',2.3485,'DriftPass')};
    
    PSTRAIGHT6A = [PS6A11 VSCREEN PS6A12 OTR WP PS6A2 WP PS6A2 WP PS6A2a CERN_CH1 PS6A2b...
                   WP PS6A2 WP PS6A2 WP OTR PS6A4 OTR WP PS6A5];
    
else
    PSTRAIGHT6A = {atdrift('PSTRAIGHT6A',6.2185,'DriftPass')};
end


PSTRAIGHT6B = {atdrift('PSTRAIGHT6B',0.4655,'DriftPass')};
PSTRAIGHT7  = {atdrift('PSTRAIGHT7',1.28,'DriftPass')};
PSTRAIGHT8  = {atdrift('PSTRAIGHT8',0.5,'DriftPass')};
PSTRAIGHT9Aa = {atdrift('PSTRAIGHT9A',4.584,'DriftPass')};
PSTRAIGHT9Ab = {atdrift('PSTRAIGHT9A',0.955,'DriftPass')};
PSTRAIGHT9A = [PSTRAIGHT9Aa BSDIOTR PSTRAIGHT9Ab];
PSTRAIGHT9B = {atdrift('PSTRAIGHT9B',0.465,'DriftPass')};
PSTRAIGHT10 = {atdrift('PSTRAIGHT10',1.14,'DriftPass')};
PSTRAIGHT11 = {atdrift('PSTRAIGHT11',0.5,'DriftPass')};
PSTRAIGHT12 = {atdrift('PSTRAIGHT12',1.404,'DriftPass')};
PSTRAIGHT13 = {atdrift('PSTRAIGHT13',2.89,'DriftPass')};
PSTRAIGHT14 = {atdrift('PSTRAIGHT14',0.5,'DriftPass')};
PSTRAIGHT15A= {atdrift('PSTRAIGHT15A',0.671,'DriftPass')};
PSTRAIGHT15Ba= {atdrift('PSTRAIGHT15B',3.2623,'DriftPass')};
PSTRAIGHT15Bb= {atdrift('PSTRAIGHT15B',1.2257,'DriftPass')};
PSTRAIGHT15B = [PSTRAIGHT15Ba BSDIOTR PSTRAIGHT15Bb];
PSTRAIGHT15C= {atdrift('PSTRAIGHT15C',0.285,'DriftPass')};
cdrift = {atdrift('cdrift',0.206,'DriftPass')};

% Booster quads
% BDQUD =  atquadrupole('BQD', 0.34, -1.016147,'QuadLinearPass');
% BFQUD =  atquadrupole('BQF', 0.34,  1.402775,'QuadLinearPass');
BDQUD =  {atquadrupole('BQD', 0.34, -1.0368349,'QuadLinearPass')};
BFQUD =  {atquadrupole('BQF', 0.34,  1.4078549,'QuadLinearPass')};

% BTS quads - original
% DQUD1 =  {atquadrupole('QUAD', 0.4,  -1.3618983,'QuadLinearPass')};
% DQUD2 =  {atquadrupole('QUAD', 0.4,  -0.46133062,'QuadLinearPass')};
% DQUD3 =  {atquadrupole('QUAD', 0.4,  -0.54609978,'QuadLinearPass')};
% DQUD4 =  {atquadrupole('QUAD', 0.4,  -0.89580103,'QuadLinearPass')};
% DQUD5 =  {atquadrupole('QUAD', 0.4,  -1.0407761,'QuadLinearPass')};
% DQUD6 =  {atquadrupole('QUAD', 0.4,  -0.88235615,'QuadLinearPass')};
% FQUD1 =  {atquadrupole('QUAD', 0.4,   1.4195575,'QuadLinearPass')};
% FQUD2 =  {atquadrupole('QUAD', 0.4,   0.63588467,'QuadLinearPass')};
% FQUD3 =  {atquadrupole('QUAD', 0.4,   0.34859322,'QuadLinearPass')};
% FQUD4 =  {atquadrupole('QUAD', 0.4,   1.0404348,'QuadLinearPass')};
% FQUD5 =  {atquadrupole('QUAD', 0.4,   1.1194183,'QuadLinearPass')};
% FQUD6 =  {atquadrupole('QUAD', 0.4,   1.0832694,'QuadLinearPass')};

% BTS quads With Zepto quad
% % BTS quads - lattice file values found on 09/09/2020
% kbts = [1.4195575,-1.3618983,-0.46133062,0.63588467,0.00000001,-0.54609978,0.34859322,-0.89580103,1.0404348,1.1194183,-1.0407761,1.0832694,-0.88235615];
if strcmpi(mode,'quad')
    % % first four quads adjusted for ZEPTO at min field
    kbts = [1.415811, -1.345263, -0.475473, 0.622622, 0.027481, -0.546145, 0.348647, -0.895842, 1.045363, 1.124549, -1.034883, 1.086121, -0.886992];
elseif strcmpi(mode,'zepto')
    % % ZEPTO adjusted for quad #4 turned off
    kbts = [1.418968, -1.295526, -0.327945, 0, 0.635889, -0.521670, 0.289932, -0.895842, 1.045363, 1.124549, -1.034883, 1.086121, -0.886992];
elseif strcmpi(mode,'prezepto')
    % BTS quads - machine values found on 09/09/2020 plus zepto off
    kbts = [1.4195152,-1.3618727,-0.46136965,0.63592728,0.00000001,-0.54614480,0.34864665,-0.89584231,1.0453633,1.1245489,-1.0348828,1.0861206,-0.88699216];
end
% % initial values from lattice file, plus ZEPTO at min field
% kbts = [1.419515, -1.361873, -0.461370, 0.635927, 0.027481, -0.546145, 0.348647, -0.895842, 1.045363, 1.124549, -1.034883, 1.086121, -0.886992];
% % initial values from lattice file, plus ZEPTO at max field
% kbts = [1.419515, -1.361873, -0.461370, 0.635927, 2.270428, -0.546145, 0.348647, -0.895842, 1.045363, 1.124549, -1.034883, 1.086121, -0.886992];
% % ZEPTO quad off, better matching at SR injection point
% kbts = [1.419515, -1.361873, -0.848671, 0.978582, 1e-12, -0.870610, 0.785544, -0.908008, 1.170100, 1.265984, -1.016815, 1.048485, -0.815656];
% % first four quads adjusted for ZEPTO at min field plus better matching to SR septum
% kbts = [1.416868, -1.349843, -0.852292, 0.960417, 0.027481, -0.870610, 0.785544, -0.908008, 1.170100, 1.265984, -1.016815, 1.048485, -0.815656];
% % ZEPTO adjusted for quad #4 turned off plus better macthing to SR septum
% kbts = [1.467679, -1.375174, -0.607793, 1e-12, 0.966589, -0.896164, 0.717672, -0.908008, 1.170100, 1.265984, -1.016815, 1.048485, -0.815656];

FQUD1 =  {atquadrupole('QUAD',  0.4,  kbts(1), 'QuadLinearPass')};
DQUD1 =  {atquadrupole('QUAD',  0.4,  kbts(2), 'QuadLinearPass')};
DQUD2 =  {atquadrupole('QUAD',  0.4,  kbts(3), 'QuadLinearPass')};
FQUD2 =  {atquadrupole('QUAD',  0.4,  kbts(4), 'QuadLinearPass')};
ZEPTO =  {atquadrupole('ZEPTO', 0.3,  kbts(5), 'StrMPoleSymplectic4Pass')};  % tuneable from 22.72 T/m to 0.275 T/m
DQUD3 =  {atquadrupole('QUAD',  0.4,  kbts(6), 'QuadLinearPass')};
FQUD3 =  {atquadrupole('QUAD',  0.4,  kbts(7), 'QuadLinearPass')};
DQUD4 =  {atquadrupole('QUAD',  0.4,  kbts(8), 'QuadLinearPass')};
FQUD4 =  {atquadrupole('QUAD',  0.4,  kbts(9), 'QuadLinearPass')};
FQUD5 =  {atquadrupole('QUAD',  0.4,  kbts(10),'QuadLinearPass')};
DQUD5 =  {atquadrupole('QUAD',  0.4,  kbts(11),'QuadLinearPass')};
FQUD6 =  {atquadrupole('QUAD',  0.4,  kbts(12),'QuadLinearPass')};
DQUD6 =  {atquadrupole('QUAD',  0.4,  kbts(13),'QuadLinearPass')};

% correctors
HBTSC1 = {atcorrector('HSTR',1e-6,[ 0 0 ],'CorrectorPass')};
VBTSC1 = {atcorrector('VSTR',1e-6,[ 0 0 ],'CorrectorPass')};
BTSC1 = [HBTSC1 cdrift VBTSC1];
BTSC2 = [HBTSC1 cdrift VBTSC1];
BTSC3 = [HBTSC1 cdrift VBTSC1];
BTSC4 = [HBTSC1 cdrift VBTSC1];
BTSC5 = [HBTSC1 cdrift VBTSC1];
BTSC6 = [HBTSC1 cdrift VBTSC1];
BTSC7 = [HBTSC1 cdrift VBTSC1];

hk = {atcorrector('HSTRK',1e-6,[ 0 0 ],'CorrectorPass')};
hkdrift = {atdrift('hkdrift', .08E+00,'DriftPass')};
HKICKER = [hkdrift hk hkdrift];
vk = {atcorrector('VSTRK',1e-6,[ 0 0 ],'CorrectorPass')};
vkdrift = {atdrift('vkdrift', .08E+00,'DriftPass')};
VKICKER = [vkdrift vk vkdrift];

% Bending
BBANGLE=0.174533;
BEND1  =   {atsbend('BBTS', 2.16, 'BendingAngle', BBANGLE, 'EntranceAngle', BBANGLE/2, 'ExitAngle', BBANGLE/2, 'PassMethod', 'BendLinearPass')};
        
BANGLEFK=-0.003; % AP-BST-REP-0049: 3 mrad
FK      =  {atsbend('FK', 1.0, 'BendingAngle', BANGLEFK, 'EntranceAngle', BANGLEFK/2, 'ExitAngle', BANGLEFK/2, 'PassMethod', 'BendLinearPass')};

BAPS = -0.00466; % AP-BST-REP-0049: 4.66 mrad
PS  =  {atsbend('PS', 0.36, 'BendingAngle', BAPS, 'EntranceAngle', BAPS/2, 'ExitAngle', BAPS/2, 'PassMethod', 'BendLinearPass')};
        
BANGLEMS=-0.10803; % AP-BST-REP-0049: 108.03 mrad
MS      =  {atsbend('MS', 1.2, 'BendingAngle', BANGLEMS, 'EntranceAngle', BANGLEMS/2, 'ExitAngle', BANGLEMS/2, 'PassMethod', 'BendLinearPass')};

% the booster quads act to bend the reference trajectory
% see booster_extraction.m and AP-BST-REP-0038
% thDQ1S = -0.001541/2;
% thFQ1S =  0.009597/2;
% thDQ2S = -0.005793/2;
% thDQ1S = -0.001541/2;
% thFQ1S =  0.009597/2;
% thDQ2S = -0.006311/2;
% DQ1S      =  {atsbend('DQ1S', 0, 'BendingAngle', thDQ1S, 'EntranceAngle', 0, 'ExitAngle', 0, 'PassMethod', 'BendLinearPass')};
% FQ1S      =  {atsbend('FQ1S', 0, 'BendingAngle', thFQ1S, 'EntranceAngle', 0, 'ExitAngle', 0, 'PassMethod', 'BendLinearPass')};
% DQ2S      =  {atsbend('DQ2S', 0, 'BendingAngle', thDQ2S, 'EntranceAngle', 0, 'ExitAngle', 0, 'PassMethod', 'BendLinearPass')};
DQ1S      =  {atmarker('DQ1S', 'IdentityPass')};
FQ1S      =  {atmarker('FQ1S', 'IdentityPass')};
DQ2S      =  {atmarker('DQ2S', 'IdentityPass')};

BABEND=0.314159;
PBEND1  =  {atsbend('BB', 2.17, 'BendingAngle', BABEND, 'EntranceAngle', BABEND/2, 'ExitAngle', BABEND/2, 'PassMethod', 'BendLinearPass')};
PBEND2  =  {atsbend('BB', 2.17, 'BendingAngle', BABEND, 'EntranceAngle', BABEND/2, 'ExitAngle', BABEND/2, 'PassMethod', 'BendLinearPass')};
PBEND3  =  {atsbend('BB', 2.17, 'BendingAngle', BABEND, 'EntranceAngle', BABEND/2, 'ExitAngle', BABEND/2, 'PassMethod', 'BendLinearPass')};

BASEPTUM = 0.15;
SRSEPTUM  =  {atsbend('SRSEPTUM', 1.9, 'BendingAngle', BASEPTUM, 'EntranceAngle', BASEPTUM/2, 'ExitAngle', BASEPTUM/2, 'PassMethod', 'BendLinearPass')};

BTSBPM1 = {atmarker('BPM', 'IdentityPass')};
BTSBPM2 = {atmarker('BPM', 'IdentityPass')};
BTSBPM3 = {atmarker('BPM', 'IdentityPass')};
BTSBPM4 = {atmarker('BPM', 'IdentityPass')};
BTSBPM5 = {atmarker('BPM', 'IdentityPass')};
BTSBPM6 = {atmarker('BPM', 'IdentityPass')};
BTSBPM7 = {atmarker('BPM', 'IdentityPass')};
ECOLL = {atmarker('ECOLL', 'IdentityPass')};
EP = {atmarker('EP', 'IdentityPass')};
IP      =  {atmarker('IP', 'IdentityPass')};
HCOLL1 = {atmarker('HCOLL1', 'IdentityPass')};
HCOLL2 = {atmarker('HCOLL2', 'IdentityPass')};
VCOLL1 = {atmarker('VCOLL1', 'IdentityPass')};
VCOLL2 = {atmarker('VCOLL2', 'IdentityPass')};

% Begin Lattice
BTS = [BFQUD, DFT1530, FK, DFT250, DFT200, VKICKER, DFT10, BPM,...
DFT60, DQ1S, BDQUD, DQ1S, DFT520, BEND1, DFT300, HKICKER, DFT120, ...
FQ1S, BFQUD, FQ1S, DFT250, MPS, PS, DFT2170, DFT200, VKICKER, DFT120, ...
DQ2S, BDQUD, DQ2S, DFT580, MMS, MS, DFT180, EP,...
BSEPTTOQA, BTSC1, BSEPTTOQB, BTSBPM1, BSEPTTOQC, HCOLL1, BPMSEP1,...
FQUD1, PSTRAIGHT1, DQUD1, CORRSEP, BTSC2, PSTRAIGHT2, BTSBPM2, BPMSEP,...
DQUD2, PSTRAIGHT3, FQUD2, CORRSEP, BTSC3, PSTRAIGHT4A, ZEPTO, PSTRAIGHT4B, VCOLL1,...
PSTRAIGHT4C, BTSBPM3, BPMSEP, DQUD3, PSTRAIGHT5, FQUD3, CORRSEP,...
BTSC4, PSTRAIGHT6A, HCOLL2, PSTRAIGHT6B, PBEND1, PSTRAIGHT7, BTSBPM4,...
BPMSEP, DQUD4, PSTRAIGHT8, FQUD4, CORRSEP, BTSC5, PSTRAIGHT9A, ECOLL,...
PSTRAIGHT9B, PBEND2, PSTRAIGHT10, BTSBPM5, BPMSEP, FQUD5, PSTRAIGHT11,...
DQUD5, CORRSEP, BTSC6, PSTRAIGHT12, WP, PBEND3, PSTRAIGHT13, BTSBPM6,...
BPMSEP, FQUD6, PSTRAIGHT14, DQUD6, CORRSEP, BTSC7, PSTRAIGHT15A,...
VCOLL2, PSTRAIGHT15B, WP, BTSBPM7, PSTRAIGHT15C, SRSEPTUM, IP];
            
THERING = BTS;

evalin('caller','global THERING GLOBVAL');
disp('** Done **');
