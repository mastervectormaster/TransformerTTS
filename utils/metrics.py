import numpy as np
import tensorflow as tf


def attention_score(att, mel_len, phon_len, r):
    """
    returns a tuple of scores (loc_score, sharp_score), where loc_score measures monotonicity and
    sharp_score measures the sharpness of attention peaks
    attn_weights : [N, n_heads, mel_dim, phoneme_dim]
    """
    assert len(tf.shape(att)) == 4
    
    mask = tf.range(tf.shape(att)[2])[None, :] < mel_len[:, None]
    mask = tf.cast(mask, tf.int32)[:, None, :]  # [N, 1, mel_dim]
    
    # distance between max (jumpiness)
    loc_score = attention_jumps_score(att=att, mel_mask=mask, mel_len=mel_len, r=r)
    
    # variance
    peak_score = attention_peak_score(att, mask)
    
    # diagonality
    diag_score = diagonality_measure(att, mel_len, phon_len)
    
    return loc_score, peak_score, 1./diag_score


def attention_jumps_score(att, mel_mask, mel_len, r):
    max_loc = tf.argmax(att, axis=3)  # [N, n_heads, mel_max]
    max_loc_diff = tf.abs(max_loc[:, :, 1:] - max_loc[:, :, :-1])  # [N, h_heads, mel_max - 1]
    loc_score = tf.cast(max_loc_diff >= 0, tf.int32) * tf.cast(max_loc_diff <= r, tf.int32)  # [N, h_heads, mel_max - 1]
    loc_score = tf.reduce_sum(loc_score * mel_mask[:, :, 1:], axis=-1)
    loc_score = loc_score / (mel_len - 1)[:, None]
    return tf.cast(loc_score, tf.float32)


def attention_peak_score(att, mel_mask):
    max_loc = tf.reduce_max(att, axis=3)  # [N, n_heads, mel_dim]
    peak_score = tf.reduce_mean(max_loc * tf.cast(mel_mask, tf.float32), axis=-1)
    return tf.cast(peak_score, tf.float32)


def diagonality_measure(att, mel_len, phon_len):
    batch_size = tf.shape(att)[0]
    mel_size = tf.shape(att)[2]
    phon_size = tf.shape(att)[3]
    diag_mask = []
    for i in range(batch_size):
        d_mask = weight_mask(mel_len[i], phon_len[i], padded_shape=(mel_size, phon_size))
        diag_mask.append(d_mask)
    diag_mask = tf.cast(tf.stack(diag_mask), tf.float32)[:, None, :, :]
    diag_score = tf.reduce_sum(att * diag_mask, axis=-1)
    diag_score = tf.reduce_sum(diag_score, axis=-1)
    return tf.cast(diag_score, tf.float32)


def weight_mask(mel_len, phon_len, padded_shape):
    """ exponential loss mask based on distance from euclidean diagonal"""
    max_m = mel_len
    max_n = phon_len
    i = np.tile(np.arange(max_n), (max_m, 1)) / max_n
    j = np.swapaxes(np.tile(np.arange(max_m), (max_n, 1)), 0, 1) / max_m
    mask = np.sqrt(np.square(i - j))
    expanded_mask = np.zeros(padded_shape)
    expanded_mask[0:mel_len, 0:phon_len] = mask
    return expanded_mask
