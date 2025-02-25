# This file is part of the LSST Solar System Processing lsstssp.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
lsstssp

LSST Solar System Processing routines for
linking of observations of moving objects.

Formerly known as MOPS. Algorithm: Based on HelioLinC (Holman et al. 2018)
we transform topocentric observations to heliocentric states assuming a
distance and radial velocity. The resulting 3D positions are collected into
tracklets. Tracklets contain at least two observations and can,
thus, be used to create velocity vectors. A tracklet + velocity vector is
called an "arrow". Arrows are propagated to a common epoch using spiceypy's
2body propagator, and then clustered using dbscan.

Implementation: S. Eggl 20191215
"""

# Temporary modules:
#from thor.orbits import iod

# Accelerators
import numpy as np
import numba

# Database
import pandas as pd

# Orbital Dynamics
import spiceypy as sp

# Clustering
import scipy.spatial as sc
import sklearn.cluster as cluster

# Trimmed mean
from scipy import stats

# Accelerated vector operations
from . import vector as vc

# Constants such as the speed of light and GM
from . import constants as cn

# Coordinate transfroms
from . import transforms as tr

# Orbital Dynamics 
from . import propagate as pr

# Ephemeris generator
from . import ephemeris as ephem

# Utility functions
from . import utility as ut


__all__ = [ 'heliolinc2','obs2heliolinc',
           'selectTrackletsFromObsData', 'cullSameTimePairs',
           'makeHeliocentricArrows', 'observationsInCluster', 
           'meanArrowStatesInClusters','observationsInArrows',
           'collapseClusterSubsets', 'deduplicateClusters']


############################################
# MODULE SPECIFIC EXCEPTION
###########################################

class Error(Exception):
    """HelioLinC3D module specific exception."""
    pass


############################################
# OBSERVATIONS, TRACKLETS AND ARROWS
###########################################


def obs2heliolinc(df, uniqueObsId=False, uniqueObsIdName="obsId", 
                  timeName="FieldMJD", raName="AstRA(deg)", 
                  decName="AstDec(deg)", observerLocation='I11',
                  observerEphemerisDt='1h', observer_xyz=[], 
                  observer_vxyz=[]):
    
    """Converts observations in pandas DataFrame to HelioLinC3D ingestable format.
    
    Parameters:
    ------------
    df                 ... pandas DataFrame containing observations 
                        
    uniqueObsId        ... True/False: If a unique observation identifier 
                           is present in the dataframe use that, 
                           otherwise create that here.
    uniqueObsIdName    ... what is the name of the unique observation identifier?
    fieldIdName        ... name of observed field identifier
    timeName           ... name of time identifier column
    raName             ... name of Right Ascension column
    decName            ... name of Declination column
    observerLocation   ... Observer location Minor Planet Center code (e.g. 'I11')
    observerEphemerisDt... Sampling rate for observer heliocentric ephemeris query (e.g. '1h')
    observer_xyz       ... numpy array, heliocentric observer locations at observation epochs 
                           in ICRF [au] if known. If empty, states will be retrieved
                           from JPL horizons online.
    observer_vxyz      ... numpy array, heliocentric observer velocity states in ICRF [au/day]. 
                           If empty, states will be retrieved from JPL horizons online.
                  
                           
                           
    """
    required_input_columns=['time','RA','DEC']
                      
    required_output_columns=['obsId','obsName','time','RA','DEC',
                      'x_obs','y_obs','z_obs',
                     'vx_obs','vy_obs','vz_obs']

      
    # Create a copy with only required inputs
    df2 = df[[timeName,raName,decName]]
     
    # print(df2)    
    # Rename columns of observations DataFrame to work with HelioLinC3D
    column_mapping = {timeName:"time",raName:"RA", decName:"DEC"}    
    df2.rename(columns = column_mapping, inplace=True)
  
    # Sort by observation time
    # df2.sort_values(by=['time','RA'], inplace=True)
    
    df2.reset_index(inplace=True, drop=False)
    
    # Create observation ID         
    df2['obsId'] = df2.index
    
    # print(df2)
    # If a unique observation Identifier is present in the dataframe use that
    if (uniqueObsId):
        df2['obsName'] = df[uniqueObsIdName].values.astype(str)
    # Otherwise create your own
    else:    
        df2['obsName'] = df2['obsId'].values.astype(str)
    
    
    df2['night']=(ut.lsstNight(df2['time'],df2['time'].min())).astype(int)
  
    # if states of observatory at observation epochs are not provided,
    # download them from JPL Horizons
    if not observer_xyz:
  
        # Epochs of observation
        obs_epochs=tr.mjd2jd(df2['time'].values)
        # Grab
        [observer_xyz, observer_vxyz]=ephem.getObserverStates(obs_epochs,
                                                          observerLocation,
                                                          observerEphemerisDt)
    # Add observer states to observations DataFrame
    df2['x_obs']=observer_xyz[:,0]
    df2['y_obs']=observer_xyz[:,1]
    df2['z_obs']=observer_xyz[:,2]
    df2['vx_obs']=observer_vxyz[:,0]
    df2['vy_obs']=observer_vxyz[:,1]
    df2['vz_obs']=observer_vxyz[:,2]
    
    
    # Check if all required columns are present
    for col in required_output_columns:
           if col not in df2.columns:
                raise Exception("Error in obs2heliolinc: required columns not present.")
    
    return df2


def cullSameTimePairs(pairs, df, dt_min, dt_max, time_column_name):
    """Cull all observation pairs that occur at the same time.

    Parameters:
    -----------
    pairs             ... array of observation indices that form a tracklet
                          (only 2 entries are supported for now)
    df                ... pandas dataframe containing observation data
    dt_min            ... minimum timespan between two observations 
                          to be considered a pair, e.g. exposure duration (days)
    dt_max            ... maximum timespan between two observations 
                          to be considered a pair (days)
    time_column_name  ... string, the name of the pandas dataframe column
                          containing the epoch of each observation

    Returns:
    --------
    goodpairs         ... array of observation indices that form possible
                          tracklets (only 2 observation entries
                          per tracklet are supported for now)
    """

    tn = time_column_name
    # Tracklets from observation paris cannot be constructed from contemporal observations (delta_t==0)
    # nor observations that are too far apart (>= dt_max)
    delta_t = np.abs(df[tn][pairs[:,1]].values-df[tn][pairs[:,0]].values)
    goodpairs = pairs[(delta_t>dt_min) & (delta_t<dt_max)]
    return np.array(goodpairs)
    
    
def selectTrackletsFromObsData(pairs, df, dt_min, dt_max, time_column_name):
    """Select data in trackelts from observations data frame.

    Parameters:
    -----------
    pairs             ... array of observation indices that form a tracklet
                          (only 2 entries are supported for now)
    df                ... pandas dataframe containing observation data
    dt_min            ... minimum timespan between two observations 
                          to be considered a pair, e.g. exposure duration (days)
    dt_max            ... maximum timespan between two observations 
                          to be considered a pair (days)
    time_column_name  ... string, the name of the pandas dataframe column
                          containing the epoch of each observation

    Returns:
    --------
    df2               ... pandas dataframe containing only observations
                          that occur in tracklets.
    goodpairs         ... array of observation indices that form possible
                          tracklets (only 2 observation entries per
                          tracklet are supported for now)
    """
    goodpairs = cullSameTimePairs(pairs, df, dt_min, dt_max, time_column_name)
    index_list = np.unique(goodpairs.flatten())
    #df2 = (df.iloc[index_list]).reset_index()

    return df, goodpairs

def makeHeliocentricArrows(df, r, drdt, tref, cr, ct_min, ct_max, v_max=1., eps=0,
                           lttc=False, filtering=True, verbose=False, 
                           leafsize=16, balanced_tree=True, n_jobs=1, frame='ecliptic', 
                           GM=cn.GM):

    """Create tracklets/arrows from dataframe containing nightly RADEC observations
    and observer positions.

    Parameters:
    -----------
    df       ... Pandas DataFrame containing nightly RA and DEC [deg], time [JD, MJD],
                 (x,y,z)_observer positions [au, ICRF]
    r        ... assumed radius of heliocentric sphere used for arrow creation[au]
    drdt     ... assumed radial velocity
    tref     ... reference time for arrow generation. Used to calculate how much the 
                 heliocentric distance changes between observations based on assumed dr/dt
    cr       ... maximum spacial clustering radius for arrow creation (au)
    ct_min   ... minimum temporal clusting radius for arrow creation (days)
    ct_max   ... maximum temporal clusting radius for arrow creation (days)


    Keyword arguments:
    ------------------
    v_max (optional)       ... velocity cutoff [au/day]
    lttc (optional)        ... light travel time correction
    filtering (optional)   ... filter created tracklets (exclude tracklets built 
                               from data with the same timestamp) 
    verbose (optional)     ... print verbose progress statements  
    eps (optional)         ... Branches of the Kdtree are not explored if their 
                               nearest points are further than r/(1+eps), 
                               and branches are added in bulk if their furthest points 
                               are nearer than r * (1+eps). eps has to be non-negative.
    leafsize               ... cKDTree leafsize 
    balanced_tree          ... cKDTree: if True median is used 
                               instead of mean to calculate box centers, more robust but 
                               leads to longer tree build times
    n_jobs                 ... number of available processors for simultaneous cKDTree query
    frame                  ... frame of reference for heliocentric arrows: 'icrf' or 'ecliptic'
    GM                     ... gravitational constant * mass for central body (e.g. gaussk**2*M_sun)                    


    Returns:
    --------
    x         ... tracklet/arrow position (3D) [au]
    y         ... tracklet/arrow velocity (3D) [au]
    t         ... tracklet/arrow reference epoch [JD/MJD]
    goodpairs ... index pairs of observations that go into each tracklet/arrow
    """
    
    goodpairs=[]
    paris=[]

    # Transform RADEC observations into positions on the unit sphere (ICRF)
    xyz = tr.radec2icrfu(df['RA'], df['DEC'], deg=True)

    # Those are the line of sight (LOS) vectors
    los_icrf = np.array([xyz[0], xyz[1], xyz[2]]).T

    # Transform LOS vectors to frame of choice
    inframe='icrf'
    los = tr.frameChange(los_icrf, inframe, frame) 
    
    # Use the position of the observer and the LOS to project the position of
    # the asteroid onto a heliocentric great circle with radius r
    observer = df[['x_obs', 'y_obs', 'z_obs']].values

    # Calculate how much the heliocentric distance changes
    # during the obsevations based on assumed dr/dt
    dt = tref-df['time'].values
    dr = (drdt-GM/(r*r)*dt/2)*dt
    r_plus_dr = r+dr

    # Heliocentric postions of the observed asteroids
    posu = vc.sphereLineIntercept(los, observer, r_plus_dr)

    if(verbose):
        print('Heliocentric positions generated.')
        print('Building spacial KDTree...')
        
    # To generate tracklets we build our KDTree based on the positions
    # in heliocentric space
    kdtree_s = sc.cKDTree(posu, leafsize=leafsize, compact_nodes=True,
                          copy_data=False, balanced_tree=balanced_tree, 
                          boxsize=None)
    # rule out un-physical combinations of observations with kdtree

    # Query KDTree for good pairs of observations that lie within
    # the clustering radius cr
    if(verbose):
        print('KDTree generated. Creating tracklets...')
        
    pairs = kdtree_s.query_pairs(cr, p=2., eps=eps, 
                                 output_type='ndarray')

    if(verbose):
        print('Tracklet candidates found:',len(pairs))

    if (filtering):
        if(verbose):
            print('Filtering arrows by time between observations...')
        
        # Discard impossible pairs (same timestamp)
        [df2, goodpairs] = selectTrackletsFromObsData(pairs, df, ct_min, ct_max, 'time')
        
        if(verbose):
            print('Tracklets filtered. New number of tracklets:',len(goodpairs))
    
    else:
        goodpairs=pairs
    
    # tracklet position for filtered pairs
    x = posu[goodpairs[:,0]]
    # tracklet time
    t = df['time'][goodpairs[:,0]].values
    # tracklet velocity through forward differencing
    va = []
    vapp = va.append
    dt = df['time'][goodpairs[:,1]].values-df['time'][goodpairs[:,0]].values
    dx = posu[goodpairs[:,1]]-posu[goodpairs[:,0]]
    for d in range(0,3):
        vapp(np.divide(dx[:,d],dt))
    v = np.array(va).T
    
    if (filtering):
        if(verbose):
            print('Filtering arrows by max velocity...')
        vnorm=vc.norm(v)
        v_idx=np.where(vnorm<=v_max)[0]
    
        goodpairs=np.take(goodpairs,v_idx,axis=0)
        x=np.take(x,v_idx,axis=0)
        v=np.take(v,v_idx,axis=0)
        t=np.take(t,v_idx,axis=0)
    
    if(verbose):
        print('Tracklets created:',len(goodpairs))
    
    # correct arrows for light travel time
    if(lttc):
        if(verbose):
            print('(Linear correction for light travel time aberration...')
        xo = observer[goodpairs[:, 0]]
        dist = vc.norm(x-xo)
        xl = x.T-dist/cn.CAUPD*v.T
        x = xl.T 
 
    return x, v, t, goodpairs


    
def heliolinc2(dfobs, r, drdt, cr_obs, cr_arrows, ct_min, ct_max, 
               clustering_algorithm='dbscan', clustering_dimensions=6, light_time=False, verbose=True, 
               min_samples=6, n_jobs=1, mean_state_variance_limit=0):

    """HelioLinC2 (Heliocentric Linking in Cartesian Coordinates) algorithm.

    Parameters:
    -----------
    dfobs     ... Pandas DataFrame containing observation ID (obsId),
                  time, night, RA [deg], DEC[deg], observer ICRF x,y,z [au] 


    r         ... assumed heliocentric distance [au]
    drdt      ... dr/dt assumed heliocentric radial velocity [au/day]
    cr_obs    ... clustering radius for observations mapped to heliocentric positions [au]
    cr_arrows ... clustering radius for propagated arrows [au]
    ct_min    ... minimum timespan between observations to allow for trackelt making [days]
    ct_max    ... maximum timespan between observations to allow for tracklet making [days]

    
    Keyword Arguments:
    ------------------
    clustering_algorithm     ... clustering_algorithm (currently either 'dbscan' or 'kdtree')
    clustering_dimensions    ... dimensions for clustering: 3 for position space, 6 for phase space
    light_time               ... Light travel time correction
    verbose                  ... Print progress statements
    min_samples              ... minimum number of samples for clustering with dbscan
    n_jobs                   ... number of processors used for 2body propagation, dbscan and KDTree query
    mean_state_variance_limit... mean_state filtering for variance (e.g. 1e-7) 
                                 increases purity but decreases completeness 

    Returns:
    --------
    obs_in_cluster_df    ... Pandas DataFrame containing linked observation clusters (no prereduction), 
                             r, dr/dt, mean cluster state (ICRF)
    """

    xar = []
    var = []
    tar = []
    obsids_night = []
    
    xar_add = xar.append
    var_add = var.append
    tar_add = tar.append
    obsids_night_add = obsids_night.append

    # the following two arrays are for testing purposes only

    # objid_night = []
    # tobs_night = []
    
    # objid_night_add =  objid_night.append
    # tobs_night_add = tobs_night.append
    
    vnorm=vc.norm

    df_grouped_by_night=dfobs.groupby('night')
    nnights=len(df_grouped_by_night.groups)
    
    for n in df_grouped_by_night.groups.keys():
        if (verbose):
            print('Processing night ',n)
        # SELECT NIGHT FROM OBSERVATIONS DATA BASE
        idx=df_grouped_by_night.groups[n].values
        df=dfobs.loc[idx,:].reset_index(drop=True)
        tref=(dfobs['time'].max()+dfobs['time'].min())*0.5

        # GENERATE ARROWS / TRACKLETS FOR THIS NIGHT
        [xarrow_night, 
         varrow_night, 
         tarrow_night, 
         goodpairs_night]=makeHeliocentricArrows(df,r,drdt,tref,cr_obs,ct_min,
                                                     ct_max,v_max=1,lttc=light_time, eps=cr_obs,
                                                     filtering=True, verbose=False, 
                                                     leafsize=16, balanced_tree=False, n_jobs=n_jobs,
                                                     frame='ecliptic')
        # ADD TO PREVIOUS ARROWS
        if (len(xarrow_night)<1):
            if (verbose):
                print('no data in night ',n)
        else:
            xar_add(xarrow_night)
            var_add(varrow_night)
            tar_add(tarrow_night)
            obsids_night_add(df['obsId'].values[goodpairs_night])

            #objid_night_add(df['objId'].values[goodpairs_night])
            #tobs_night_add(df['time'].values[goodpairs_night])

    if (len(xar)<1):
        if (verbose):
            print('No arrows for the current r, dr/dt pair. ',n)
    else:    
        xarrow=np.vstack(xar)
        varrow=np.vstack(var)
        tarrow=np.hstack(tar)
        
#       Which observations are in each arrow? -> obsids        
        obsids=np.vstack(obsids_night)
    
        if(verbose):
            print('tarrow', tarrow)
            print('obsids', obsids)

#   # the following two arrays are for testing purposes only
        #objids=np.vstack(objid_night)
        #tobs=np.vstack(tobs_night)

#   # PROPAGATE ARROWS TO COMMON EPOCH
        if (verbose):
            print('Propagating arrows...')
            
#   # propagate arrows to the center of the observational arc    
        tprop=(dfobs['time'].max()+dfobs['time'].min())*0.5
        [xp, vp, dt] = pr.propagateState(xarrow, varrow, tarrow, tprop,
                                         propagator='2body', n_jobs=n_jobs)

        xpvp=np.hstack([xp,vp])
#       # nomalize v vector to have approximately the same magnitude as xp to help with 6D clustering
        if (clustering_dimensions==6):
            vnormr=(r/vnorm(vp))
            vpn=vp*np.array([vnormr,vnormr,vnormr]).T
            xpvpn=np.hstack([xp,vpn])
        
        if (verbose):
            print('Propagated arrows', xpvp)
        
#       # CLUSTER WITH DBSCAN
        if (verbose):
            print('Clustering arrows...')
            
#       # CLUSTER PROPAGATED STATES (COORDINATE SPACE (xp) OR PHASE SPACE (xpvp)               
        if(clustering_algorithm=='dbscan'):
            if (clustering_dimensions==6):
                db=cluster.DBSCAN(eps=cr_arrows, min_samples=min_samples, n_jobs=n_jobs).fit(xpvpn)
            elif (clustering_dimensions==3):
                db=cluster.DBSCAN(eps=cr_arrows, min_samples=min_samples, n_jobs=n_jobs).fit(xp)
            else:
                raise Exception('Error: only clustering in 3 or 6 dimensions supported.')
#       # CONVERT CLUSTER INDICES TO OBSERVATION INDICES IN EACH CLUSTER
            try:
                if (verbose):
                    print('Calculating mean arrow states in clusters...')
                [mean_states, var_states, labels2] = meanArrowStatesInClusters(xpvp, db, garbage=False, trim=25) 
                
                if (verbose):
                    print('Finding observations in clusters...')
                [obs_in_cluster, labels] = observationsInCluster(dfobs, obsids, db, garbage=False)
                obs_in_cluster_df=pd.DataFrame(zip(labels,obs_in_cluster), columns=['clusterId','obsId'])
   
        
            except: 
                raise Exception('Error: Could not construct cluster dataframe.')

#         elif (clustering_algorithm=='kdtree'):
# #       # CLUSTER WITH KDTree
#             if (verbose):
#                 print('Clustering arrows...')
#             tree = sc.cKDTree(xp)
#             # k, the number of neighbours to be returned should be nvisits to a field, but since we don't have that here
#             # we assume it is at most 2x per night which may be wrong for deep drilling fields
#             db = tree.query(xp, k=nnights*2, p=2, distance_upper_bound=cr_arrows, n_jobs=n_jobs)

#             if (verbose):
#                 print('Deduplicating observations in clusters...')
#             obs = []
#             obs_app = obs.append
#             arrow_idx = np.array(db,dtype="int64")[1]
#             nan_idx = arrow_idx.shape[0]
#             for i in arrow_idx:
#                 entries = i[i<nan_idx]
#                 if(len(entries)) > 1:
#                      obs_app([np.unique(np.ravel(obsids[entries]))])

#             obs_in_cluster_df = pd.DataFrame(obs,columns=['obsId'])
#             obs_in_cluster_df['clusterId']=obs_in_cluster_df.index.values
#             obs_in_cluster_df=obs_in_cluster_df[['clusterId','obsId']]

#             mean_states=[]
#             var_states=[]
        else:
            raise Exception('Error: no valid clustering algorithm selected') 

    
        # Add heliocentric r, dr/dt, epoch and clipped mean states (ICRF) to pandas DataFrame
        obs_in_cluster_df['r'] = r
        obs_in_cluster_df['drdt'] = drdt
        obs_in_cluster_df['cluster_epoch'] = tprop
        
        if (len(mean_states) < 1):
            obs_in_cluster_df[['x_ecl','y_ecl','z_ecl','vx_ecl',
                               'vy_ecl','vz_ecl','var_pos','var_vel']] = pd.DataFrame([np.zeros(8)],                                                                                                            index=obs_in_cluster_df.index)
        else:
            obs_in_cluster_df['x_ecl'] = mean_states[:,0]
            obs_in_cluster_df['y_ecl'] = mean_states[:,1]
            obs_in_cluster_df['z_ecl'] = mean_states[:,2]
            obs_in_cluster_df['vx_ecl'] = mean_states[:,3]
            obs_in_cluster_df['vy_ecl'] = mean_states[:,4]
            obs_in_cluster_df['vz_ecl'] = mean_states[:,5]
            
            obs_in_cluster_df['var_pos'] = vnorm(var_states[:,0:3])
            obs_in_cluster_df['var_vel'] = vnorm(var_states[:,3:6])
        
        if (mean_state_variance_limit>0):
            if (verbose):
                print('Filtering clusters for mean state variance...')
            obs_in_cluster_df = obs_in_cluster_df[
                                (obs_in_cluster_df['var_pos']<=mean_state_variance_limit)].reset_index(drop=True)  

        return obs_in_cluster_df
    
    
def deduplicateClusters(cdf):    
    """Deduplicate clusters produced by helioLinC2 
    based on similar observations (r,rdot are discarded)

    Parameters:
    -----------
    cdf ... Pandas DataFrame containing object ID (objId), observation ID (obsId)
              
    Returns:
    --------
    cdf2     ... deduplicated Pandas DataFrame 
    """
    
#   cdf2=(cdf.iloc[cdf.astype(str).drop_duplicates(
#         subset='obsId',keep="first").index]).reset_index(drop=True)    

    cdf['clusterObs'] = cdf['obsId'].astype(str) 
    cdf.sort_values(by=['clusterObs','var_pos','var_vel'],inplace=True)
    cdf.drop_duplicates(subset='clusterObs',keep="first",ignore_index=True, inplace=True)
    return cdf.drop(columns=['clusterObs'])
        
def collapseClusterSubsets(cdf):
    """Merge clusters that are subsets of each other 
    as produced by HelioLinC2.

    Parameters:
    -----------
    cdf ... Pandas DataFrame containing object ID (objId), observation ID (obsId)
              
    Returns:
    --------
    cdf2                ... collapsed Pandas DataFrame 
    subset_clusters     ... indices of input dataframe (cdf) that are subsets
    subset_cluster_ids  ... linked list of cluster ids [i,j] where j is a subset of i
    """
    
   
    #for index, row in clusters_df.iterrows():
    vals=cdf.obsId.values
    subset_clusters=[]
    subset_clusters_app=subset_clusters.append
    subset_cluster_ids=[]
    subset_cluster_ids_app=subset_cluster_ids.append

    cdf_idx=range(0,len(cdf))

    vals_set=[]
    vals_set_app=vals_set.append
    vals_min=[]
    vals_min_app=vals_min.append
    vals_max=[]
    vals_max_app=vals_max.append

    for i in cdf_idx:
        vals_set_app(set(vals[i]))          
        vals_min_app(np.min(vals[i]))
        vals_max_app(np.max(vals[i]))         

    vmin=np.array(vals_min)
    vmax=np.array(vals_max)

    for i in cdf_idx:
        for j in cdf_idx:
            if(i != j):
                    #use the fact that we have ordered sets here
                    if(vmax[i]<vmin[j]):
                        break
                    elif(vmin[i]>vmax[j]):
                        break
                    else:
                        is_subset=vals_set[i].issubset(vals_set[j])

                        if(is_subset):
                            subset_clusters_app(i)
                            subset_cluster_ids_app([i,j])
                            break
        if(np.mod(i, 1000) == 0):                
            print('Progress [%], ', i/cdf_idx[-1]*100)

    idx_to_drop = subset_clusters
    
    cdf2=cdf.drop(index=idx_to_drop)
    return cdf2, subset_clusters, subset_cluster_ids 


def meanArrowStatesInClusters(xpvp, cluster, garbage=False, trim=25):
    """Calculate mean propagated state in each cluster.
    
    Parameters:
    -----------
    xpvp      ... array containing states for each cluster
    cluster   ... output of clustering algorithm (sklearn.cluster)
    
    Keyword Arguments:
    ------------------
    garbage   ... return results for garbage cluster in dbscan (usually index 0)
    trim      ... cutoff percentage for trimmed mean, 
                  25 would slices off ‘leftmost’ and ‘rightmost’ 25% of scores.
    
    Returns:
    --------
    mean_state     ... trimmed mean state in each cluster
    unique_labels  ... cluster labels
    """
    #cluster names (beware: -1 is the cluster of all the leftovers)
    if(garbage):
        unique_labels = np.unique(cluster.labels_)
    else:
        unique_labels = np.unique(cluster.labels_)[1:]
    #number of clusters
    n_clusters = len(unique_labels)
         
    mean_states=[]
    mean_states_add=mean_states.append
    tmean=stats.trim_mean
    
    var_states=[]
    var_states_add=var_states.append
    tvar=stats.tvar
    
    #cluster contains 
    for u in unique_labels:
        idx = np.where(cluster.labels_ == u)[0]
        
        # trimmed mean state in this cluster
        mean_states_add(tmean(xpvp[idx,:], trim/100, axis=0))
        # trimmed variance in this cluster
        var_states_add(tvar(xpvp[idx,:], axis=0, ddof=1))
    return np.array(mean_states), np.array(var_states), unique_labels  


def observationsInCluster(df, pairs, cluster, garbage=False):
    """List observations in each cluster.
    
    Parameters:
    -----------
    df      ... pandas dataframe with observations
    pairs   ... list of pairs of observations [obsid1,obsid2] linked into arrows
    cluster ... output of clustering algorithm (sklearn.cluster)
    
    Returns:
    --------
    obs_in_cluster ... list of observations in each cluster
    """
    #cluster names (beware: -1 is the cluster of all the leftovers)
    if(garbage):
        unique_labels = np.unique(cluster.labels_)
    else:
        unique_labels = np.unique(cluster.labels_)[1:]
    #number of clusters
    n_clusters = len(unique_labels)
    
    #which objects do observations in pairs (tracklets) belong to
    p = np.array(pairs)              
    

    obs_in_cluster=[]
    obs_in_cluster_add=obs_in_cluster.append
    
    #cluster contains 
    for u in unique_labels:
        #which indices in pair array appear in a given cluster?
        idx = np.where(cluster.labels_ == u)[0]
        
        #which observations are in this cluster
        obs_in_cluster_add(np.unique(p[idx].flatten()))
        
    return obs_in_cluster, unique_labels  



def observationsInArrows(df, goodpairs, *args, **kwargs):
    """Find which observations go into an arrow.
    
    Parameters:
    -----------
    df          ... pandas dataframe with observations
    goodpairs   ... filtered list of pairs of observations [obsid1,obsid2] linked into arrows
    
    Returns:
    --------
    df_obs_in_arrows ... pandas dataframe where the index is the arrow id 
                         and the first and second column are the first and second observation 
                         that go into the respective arrow.
    """
    df_obs_in_arrows = pd.DataFrame(goodpairs,**kwargs)
    return df_obs_in_arrows


